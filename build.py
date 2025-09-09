import os
import PyInstaller.__main__
import english_words

# Get the full path to the english_words data folder
english_words_path = os.path.dirname(english_words.__file__)
data_folder = os.path.join(english_words_path, "data")

if not os.path.exists(data_folder):
    raise FileNotFoundError(f"Data folder not found: {data_folder}")

PyInstaller.__main__.run([
    '--name=WordTrial_v1.2.0',
    '--onefile',
    # '--clean', ### Force rebuild
    "--add-data", "style.tcss;.",
    # '--add-data', f'{data_folder};english_words/data', 
    # '--specpath', 'output/spec',
    'main.py',
])
