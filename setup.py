import setuptools, glob, os, fnmatch

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

    
def _process_requirements():
    packages = open('requirements.txt').read().strip().split('\n')
    requires = []
    for pkg in packages:
        if pkg.startswith('git+ssh'):
            return_code = os.system('pip install {}'.format(pkg))
            assert return_code == 0, 'error, status_code is: {}, exit!'.format(return_code)
        if pkg.startswith('./docs'):
            continue
        else:
            requires.append(pkg)
    return requires

def package_files(directory):
    import subprocess
    list_of_files = subprocess.check_output("git ls-files", shell=True).splitlines()
    return [str(k) for k in list_of_files]

extra_files = package_files('./')

setuptools.setup(
    name="void-terminal",
    version="0.0.0",
    author="Qingxu",
    author_email="505030475@qq.com",
    description="LLM based APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/binary-husky/gpt-academic",
    project_urls={
        "Bug Tracker": "https://github.com/binary-husky/gpt-academic/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    package_data={"": extra_files},
    include_package_data=True,
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.9",
    install_requires=_process_requirements(),
)