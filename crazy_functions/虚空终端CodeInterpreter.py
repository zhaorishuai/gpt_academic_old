from toolbox import CatchException, update_ui, gen_time_str, trimmed_format_exc, promote_file_to_downloadzone
from .crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from .crazy_utils import input_clipping, try_install_deps
import os

def inspect_dependency(chatbot, history):
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    return True

def get_code_block(reply):
    import re
    pattern = r"```([\s\S]*?)```" # regex pattern to match code blocks
    matches = re.findall(pattern, reply) # find all code blocks in text
    if len(matches) == 1: 
        return matches[0].strip('python') #  code block
    for match in matches:
        if 'class TerminalFunction' in match:
            return match.strip('python') #  code block
    raise RuntimeError("GPT is not generating proper code.")

def gpt_interact_multi_step(txt, file_type, llm_kwargs, chatbot, history):
    # 输入
    prompt_compose = [
        f'Your job:\n'
        f'1. write a single Python function, which takes a path of a `{file_type}` file as the only argument and returns a `string` containing the result of analysis or the path of generated files. \n',
        f"2. You should write this function to perform following task: " + txt + "\n",
        f"3. Wrap the output python function with markdown codeblock."
    ]
    i_say = "".join(prompt_compose)
    demo = []

    # 第一步
    gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
        inputs=i_say, inputs_show_user=i_say, 
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=demo, 
        sys_prompt= r"You are a programmer."
    )
    history.extend([i_say, gpt_say])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新

    # 第二步
    prompt_compose = [
        "If previous stage is successful, rewrite the function you have just written to satisfy following templete: ",
"""
```python
import ...  # Put dependencies here, e.g. import numpy as np

class TerminalFunction(object): # Do not change the name of the class, The name of the class must be `TerminalFunction`

    def run(self, path):    # The name of the function must be `run`, it takes only a positional argument.
        # rewrite the function you have just written here 
        ...
        return generated_string_or_path
```
"""
    ]
    i_say = "".join(prompt_compose); inputs_show_user = "If previous stage is successful, rewrite the function you have just written to satisfy executable templete. "
    gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
        inputs=i_say, inputs_show_user=inputs_show_user, 
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=history, 
        sys_prompt= r"You are a programmer."
    )
    code_to_return = gpt_say
    history.extend([i_say, gpt_say])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新
    


    # # 第三步
    # i_say = "Please list to packages to install to run the code above. Then show me how to use `try_install_deps` function to install them."
    # i_say += 'For instance. `try_install_deps(["opencv-python", "scipy", "numpy"])`'
    # installation_advance = yield from request_gpt_model_in_new_thread_with_ui_alive(
    #     inputs=i_say, inputs_show_user=inputs_show_user, 
    #     llm_kwargs=llm_kwargs, chatbot=chatbot, history=history, 
    #     sys_prompt= r"You are a programmer."
    # )
    # # 第三步  
    i_say = "Show me how to use `pip` to install packages to run the code above. "
    i_say += 'For instance. `pip install -r opencv-python scipy numpy`'
    installation_advance = yield from request_gpt_model_in_new_thread_with_ui_alive(
        inputs=i_say, inputs_show_user=inputs_show_user, 
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=history, 
        sys_prompt= r"You are a programmer."
    )
    
    return code_to_return, installation_advance, txt, file_type, llm_kwargs, chatbot, history

def make_module(code):
    import subprocess, sys, os, shutil

    module_file = 'gpt_fn_' + gen_time_str().replace('-','_')
    with open(f'gpt_log/{module_file}.py', 'w', encoding='utf8') as f:
        f.write(code)

    def get_class_name(class_string):
        import re
        # Use regex to extract the class name
        class_name = re.search(r'class (\w+)\(', class_string).group(1)
        return class_name

    class_name = get_class_name(code)
    return f"gpt_log.{module_file}->{class_name}"

def init_module_instance(module):
    import importlib
    module_, class_ = module.split('->')
    init_f = getattr(importlib.import_module(module_), class_)
    return init_f()





@CatchException
def 虚空终端CodeInterpreter(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, web_port):
    """
    txt             输入栏用户输入的文本，例如需要翻译的一段话，再例如一个包含了待处理文件的路径
    llm_kwargs      gpt模型参数，如温度和top_p等，一般原样传递下去就行
    plugin_kwargs   插件模型的参数，暂时没有用武之地
    chatbot         聊天显示框的句柄，用于显示给用户
    history         聊天历史，前情提要
    system_prompt   给gpt的静默提醒
    web_port        当前软件运行的端口号
    """
    # 清空历史，以免输入溢出
    history = []    

    # 基本信息：功能、贡献者
    chatbot.append([
        "函数插件功能？",
        "CodeInterpreter开源版, 此插件处于开发阶段, 建议暂时不要使用, 作者: binary-husky, 插件初始化中 ..."
    ])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 尝试导入依赖, 如果缺少依赖, 则给出安装建议
    dep_ok = yield from inspect_dependency(chatbot=chatbot, history=history) # 刷新界面
    if not dep_ok: return
    
    # 读取文件
    if ("recently_uploaded_files" in plugin_kwargs) and (plugin_kwargs["recently_uploaded_files"] == ""): plugin_kwargs.pop("recently_uploaded_files")
    recently_uploaded_files = plugin_kwargs.get("recently_uploaded_files", None)
    file_path = recently_uploaded_files[-1]
    file_type = file_path.split('.')[-1]

    # 粗心检查
    if 'private_upload' in txt:
        chatbot.append([
            "...",
            f"请在输入框内填写需求，然后再次点击该插件（文件路径 {file_path} 已经被记忆）"
        ])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return
    
    # 开始干正事
    for j in range(5):  # 最多重试5次
        try:
            code, installation_advance, txt, file_type, llm_kwargs, chatbot, history = \
                yield from gpt_interact_multi_step(txt, file_type, llm_kwargs, chatbot, history)
            code = get_code_block(code)
            res = make_module(code)
            instance = init_module_instance(res)
            break
        except Exception as e:
            chatbot.append([f"第{j}次代码生成尝试，失败了", f"\n```\n{trimmed_format_exc()}\n```\n"])
            yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 代码生成结束, 开始执行
    try:
        res = instance.run(file_path)
    except Exception as e:
        chatbot.append(["执行失败了", f"\n```\n{trimmed_format_exc()}\n```\n"])
        chatbot.append(["如果是缺乏依赖，请参考以下建议", installation_advance])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    # 顺利完成，收尾
    res = str(res)
    if os.path.exists(res):
        chatbot.append(["执行成功了，结果是一个有效文件", "结果：" + res])
        promote_file_to_downloadzone(res, chatbot=chatbot)
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新
    else:
        chatbot.append(["执行成功了", "结果：" + res])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新   

