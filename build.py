from pathlib import Path
import PyInstaller.__main__

main_script = 'main.py'
app_name = 'MoodleBot'
icon_path = 'assets/icone.ico'

args = [
    main_script,
    '--onefile',
    '--windowed',
    f'--name={app_name}',
    '--noconfirm',
    '--clean',
    '--log-level=DEBUG',
    '--add-data=assets;assets',
    '--hidden-import=tkinter',
    '--hidden-import=selenium',
]

if Path(icon_path).exists():
    args.append(f'--icon={icon_path}')

PyInstaller.__main__.run(args)