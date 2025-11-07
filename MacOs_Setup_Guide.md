# Run Obsiquery on macOS using pyenv

This guide explains how to set up and run the **Obsiquery** project on macOS using **pyenv** and an isolated virtual environment.

> **Note:** macOS comes with a system Python. Do **not** use or modify it. Always use a separate pyenv-managed Python for projects.

---

## 1. Prerequisite — pyenv must be installed

Make sure you already have **pyenv** and **pyenv-virtualenv** installed and configured in your shell.

Check with:

```bash
# check pyenv installation
pyenv --version   # prints pyenv version

# check installed Python versions
pyenv versions
```

If you see multiple Python versions listed, pyenv is working. You can proceed.

---

## 2. Confirm pyenv is using the correct Python (not system one)

```bash
# check which python is active
which python
# → should point to ~/.pyenv/versions/... not /usr/bin/python

# check active version
pyenv version
# → should show something like 3.13.5 (set by .python-version)
```

If it says “(set by PYENV_VERSION environment variable),” clear it:

```bash
unset PYENV_VERSION
pyenv shell --unset
```

Then recheck.

---

## 3. Create a virtual environment for the project

```bash
# Step 1: install the specific Python version (if not already)
pyenv install 3.13.5

# Step 2: navigate to your project folder
cd /path/to/Obsiquery

# Step 3: create a virtual environment tied to Python 3.13.5
pyenv virtualenv 3.13.5 obsiquery-3.13.5
# (creates a new isolated environment named obsiquery-3.13.5)

# Step 4: set this env as local to the project
pyenv local obsiquery-3.13.5
# (creates .python-version so pyenv auto-activates when entering folder)

# Step 5: confirm correct python
pyenv version
which python
```

When you open a new terminal and `cd` into the project, this env will auto-activate.

---

## 4. Install dependencies

```bash
# upgrade pip and tools
python -m pip install --upgrade pip setuptools wheel

# install project dependencies
pip install -r requirements.txt
```

> Comment: this installs all necessary Python packages for Obsiquery inside the new virtual environment.

---

## 6. Debugging and environment checks

Use these commands to verify the environment is active and correct.

```bash
# confirm Python path
which python          # should point to ~/.pyenv/versions/obsiquery-3.13.5/bin/python

# confirm version
python --version

# confirm pyenv environment status
pyenv version
pyenv versions
```

> Comment: these checks confirm that your shell, Python, and dependencies are aligned correctly.

---

## 7. Reset / Delete and start fresh (if issues occur)

If something breaks or you want to rebuild from scratch:

>Inside you Project Directory.

```bash

# Step 1: deactivate any active env
pyenv deactivate

# Step 2: remove the existing environment
pyenv uninstall obsiquery-3.13.5  # deletes the virtualenv

# Step 3: remove old .python-version file (if any)
rm -f .python-version

# Step 4: recreate everything cleanly
pyenv virtualenv 3.13.5 obsiquery-3.13.5
pyenv local obsiquery-3.13.5
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Comment: this process wipes out the old environment and ensures a fresh, clean setup tied to the correct Python version.

---

## 8. Best practices

* Always ensure `which python` points to pyenv’s directory.
* Never use `sudo pip install` on macOS.
* Use one virtual environment per project.

