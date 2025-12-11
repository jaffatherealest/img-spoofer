# macOS Setup Guide

Get img-spoofer running on your Mac from scratch.

## Prerequisites

### Check if you have Python 3.10+

Open Terminal and run:

```bash
python3 --version
```

You need `Python 3.10` or higher. If you get "command not found" or an older version, install Python first.

### Install Python (if needed)

**Option A: Download from python.org**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the macOS installer
3. Run it, follow the prompts

**Option B: Use Homebrew**
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.12
```

### Check if you have Git

```bash
git --version
```

If missing, macOS will prompt you to install Xcode Command Line Tools. Click "Install" when prompted.

## Install the Project

### 1. Clone the repository

```bash
cd ~/Documents  # or wherever you keep projects
git clone https://github.com/jaffatherealest/img-spoofer.git
cd img-spoofer
```

### 2. Create a virtual environment

This keeps dependencies isolated from your system Python:

```bash
python3 -m venv venv
```

### 3. Activate the virtual environment

```bash
source venv/bin/activate
```

Your terminal prompt should now show `(venv)` at the start. You'll need to run this activation command every time you open a new terminal to use the tool.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

This takes a minute. You'll see packages downloading and installing.

## Run the Tool

### Prepare your images

Put your source images in the `input/` folder:

```bash
# The input folder already exists, just add your images
cp ~/Downloads/my_photos/*.jpg input/
```

Or drag-and-drop files into `input/` using Finder.

### Generate variants

```bash
python main.py spoof --input-dir input --output-dir output --variants 10
```

### Check results

Variants appear in `output/`, organized by original filename:

```
output/
├── photo1/
│   ├── photo1_v01.jpg
│   ├── photo1_v02.jpg
│   └── ...
└── manifest.json
```

## Example Commands

```bash
# Standard run
python main.py spoof -i input -n 10

# Dry run to preview
python main.py spoof -i input -n 10 --dry-run --verbose

# For Threads/Instagram Stories
python main.py spoof -i input -n 12 --target-size 1080x1350

# Scan folder for duplicates/similar images
python main.py scan ~/Pictures/content

# Scan with JSON output
python main.py scan ~/Pictures/content --output duplicates.json

# Check PDQ hash of one image
python main.py check input/photo.jpg

# Compare original to variant
python main.py compare input/photo.jpg output/photo/photo_v01.jpg
```

## Tips

**Deactivate the virtual environment when done:**
```bash
deactivate
```

**Next time you use the tool:**
```bash
cd ~/Documents/img-spoofer
source venv/bin/activate
python main.py spoof -i input -n 10
```

**Update the tool later:**
```bash
cd ~/Documents/img-spoofer
git pull
source venv/bin/activate
pip install -r requirements.txt
```
