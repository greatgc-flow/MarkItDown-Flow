import os

files_to_update = {
    'main.ts',
    'src/converter/MarkitdownConverter.ts',
    'src/modals/FileConvertModal.ts',
    'src/modals/FolderConvertModal.ts',
    'src/modals/HistoryModal.ts',
    'src/modals/PreviewModal.ts',
    'src/modals/SelfTestModal.ts',
    'src/modals/SetupModal.ts',
    'src/modals/UrlConvertModal.ts',
    'src/services/ConversionService.ts',
    'src/utils/bundledScripts.ts',
    'src/utils/paths.ts',
    'src/utils/postprocess.ts',
    'src/utils/python.ts',
    'src/settings/SettingsTab.ts'
}

enable_comment = "\n/* eslint-enable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises */\n"

for rel_path in files_to_update:
    file_path = os.path.join(r"D:\workspace\MarkItDown-Flow", rel_path)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf8') as f:
            content = f.read()
        
        if enable_comment.strip() not in content:
            with open(file_path, 'a', encoding='utf8') as f:
                f.write(enable_comment)
            print(f"Appended to {rel_path}")

