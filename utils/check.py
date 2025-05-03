# import json
# import ast
# import os
#
#
# def extract_translation_keys_from_code(file_path):
#     """Extract all translation keys used in get_translation() calls from the Python file."""
#     with open(file_path, 'r', encoding='utf-8') as file:
#         tree = ast.parse(file.read(), filename=file_path)
#
#     translation_keys = set()
#
#     for node in ast.walk(tree):
#         if isinstance(node, ast.Call):
#             # Check if this is a call to get_translation
#             if (isinstance(node.func, ast.Name) and node.func.id == 'get_translation') or \
#                     (isinstance(node.func, ast.Attribute) and node.func.attr == 'get_translation'):
#                 # The key is the second argument (assuming user_id is first)
#                 if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
#                     translation_keys.add(node.args[1].value)
#
#     return translation_keys
#
#
# def get_existing_translation_keys(translation_file_path):
#     """Get all translation keys that exist in the translations.json file."""
#     with open(translation_file_path, 'r', encoding='utf-8') as file:
#         translations = json.load(file)
#
#     english_translations = translations.get('english', {})
#     return set(english_translations.keys())
#
#
# def find_missing_translation_keys(main_code_path, translation_file_path):
#     """Find translation keys used in code but missing from translations file."""
#     code_keys = extract_translation_keys_from_code(main_code_path)
#     existing_keys = get_existing_translation_keys(translation_file_path)
#
#     missing_keys = code_keys - existing_keys
#     return sorted(missing_keys)
#
#
# if __name__ == '__main__':
#     # Update these paths according to your system
#     main_code_path = r'C:\Users\arefa\PycharmProjects\testbot\utils\main.py'
#     translation_file_path = r'C:\Users\arefa\PycharmProjects\testbot\utils\translations.json'
#
#     if not os.path.exists(main_code_path):
#         print(f"Error: Main code file not found at {main_code_path}")
#     elif not os.path.exists(translation_file_path):
#         print(f"Error: Translation file not found at {translation_file_path}")
#     else:
#         missing_keys = find_missing_translation_keys(main_code_path, translation_file_path)
#
#         if missing_keys:
#             print("The following translation keys are used in code but missing from translations.json:")
#             for key in missing_keys:
#                 print(f'- "{key}"')
#
#             print("\nYou can add them to your translations.json like this:")
#             print('"english": {')
#             for key in missing_keys:
#                 print(f'    "{key}": "TRANSLATION_HERE",')
#             print('    ...\n}')
#         else:
#             print("All translation keys in the code have corresponding entries in translations.json")
#

import json


def load_translation_file(file_path):
    """Load a translation JSON file and return its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return None


def compare_translation_keys(english_path, amharic_path):
    """Compare translation keys between English and Amharic files."""
    # Load the translation files
    english_trans = load_translation_file(english_path)
    amharic_trans = load_translation_file(amharic_path)

    if not english_trans or not amharic_trans:
        return

    # Get all keys from both files
    english_keys = set(english_trans.keys())
    amharic_keys = set(amharic_trans.keys())

    # Find keys that are in English but not in Amharic
    missing_keys = english_keys - amharic_keys

    if missing_keys:
        print("The following keys are missing in Amharic translation:")
        for key in sorted(missing_keys):
            print(f'"{key}": "{english_trans[key]}",')
    else:
        print("All English translation keys exist in Amharic translation.")

    # Optional: Find keys that are in Amharic but not in English
    extra_keys = amharic_keys - english_keys
    if extra_keys:
        print("\nWarning: The following keys exist in Amharic but not in English:")
        for key in sorted(extra_keys):
            print(f'"{key}": "{amharic_trans[key]}",')


if __name__ == "__main__":
    # Paths to your translation files
    english_path = r"C:\Users\arefa\PycharmProjects\testbot\utils\translations\english.json"
    amharic_path = r"C:\Users\arefa\PycharmProjects\testbot\utils\translations\afar.json"

    # Compare the keys
    compare_translation_keys(english_path, amharic_path)