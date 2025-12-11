# Windows Setup Guide

Get img-spoofer running on Windows from scratch.

## Prerequisites

### Check if you have Python 3.10+

Open Command Prompt or PowerShell and run:

```cmd
python --version
```

or

```cmd
py --version
```

You need `Python 3.10` or higher.

### Install Python (if needed)

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the Windows installer
3. **Important:** Check "Add Python to PATH" during installation
4. Run the installer, follow the prompts

After installing, close and reopen your terminal, then verify:

```cmd
python --version
```

### Install Git (if needed)

Check if you have it:

```cmd
git --version
```

If missing:
1. Go to [git-scm.com/download/win](https://git-scm.com/download/win)
2. Download and run the installer
3. Use default options (just click through)

## Install the Project

### 1. Clone the repository

Open Command Prompt or PowerShell:

```cmd
cd %USERPROFILE%\Documents
git clone https://github.com/jaffatherealest/img-spoofer.git
cd img-spoofer
```

### 2. Create a virtual environment

```cmd
python -m venv venv
```

### 3. Activate the virtual environment

**Command Prompt:**
```cmd
venv\Scripts\activate
```

**PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Your prompt should now show `(venv)` at the start.

### 4. Install dependencies

```cmd
pip install -r requirements.txt
```

## Run the Tool

### Prepare your images

Put your source images in the `input\` folder. You can:
- Copy files via File Explorer
- Or use the command line:

```cmd
copy C:\Users\YourName\Downloads\*.jpg input\
```

### Generate variants

```cmd
python main.py spoof --input-dir input --output-dir output --variants 10
```

### Check results

Variants appear in `output\`:

```
output\
├── photo1\
│   ├── photo1_v01.jpg
│   ├── photo1_v02.jpg
│   └── ...
└── manifest.json
```

## Example Commands

```cmd
:: Standard run
python main.py spoof -i input -n 10

:: Dry run to preview
python main.py spoof -i input -n 10 --dry-run --verbose

:: For Threads/Instagram
python main.py spoof -i input -n 12 --target-size 1080x1350

:: Scan folder for duplicates/similar images
python main.py scan C:\Users\YourName\Pictures\content

:: Scan with JSON output
python main.py scan C:\Users\YourName\Pictures\content --output duplicates.json

:: Check PDQ hash of one image
python main.py check input\photo.jpg

:: Compare original to variant
python main.py compare input\photo.jpg output\photo\photo_v01.jpg
```

## Tips

**Deactivate the virtual environment when done:**
```cmd
deactivate
```

**Next time you use the tool:**
```cmd
cd %USERPROFILE%\Documents\img-spoofer
venv\Scripts\activate
python main.py spoof -i input -n 10
```

**Update the tool later:**
```cmd
cd %USERPROFILE%\Documents\img-spoofer
git pull
venv\Scripts\activate
pip install -r requirements.txt
```

## Common Windows Issues

**"python is not recognized"**
Python isn't in your PATH. Either:
- Reinstall Python with "Add to PATH" checked
- Or use the full path: `C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe`

**PowerShell blocks the activate script**
Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Long path errors**
Windows has a 260-character path limit. Keep the project in a short path like `C:\code\img-spoofer` instead of deeply nested folders.
