import os
import shutil

SRC_ROOT = "/Users/anandagarwal/dsm_project/census_downloads_2001"
DEST_ROOT = "/Users/anandagarwal/dsm_project/census_downloads_2001_renamed"

def get_category(filename):
    if "_SC" in filename:
        return "SC"
    elif "_ST" in filename:
        return "ST"
    else:
        return "TOTAL"

def clean_state_name(filename):
    # Remove prefix and suffix to extract state name cleanly
    name = filename.replace(".xls", "").replace(".xlsx", "")
    
    # remove table prefix (C-02_, C-03_, etc.)
    parts = name.split("_", 1)
    if len(parts) > 1:
        name = parts[1]

    # remove SC/ST suffix
    name = name.replace("_SC", "").replace("_ST", "")

    return name

def main():
    os.makedirs(DEST_ROOT, exist_ok=True)

    for folder in os.listdir(SRC_ROOT):
        src_folder_path = os.path.join(SRC_ROOT, folder)

        if not os.path.isdir(src_folder_path):
            continue

        print(f"\n📂 Processing {folder}")

        for file in os.listdir(src_folder_path):
            if not (file.endswith(".xls") or file.endswith(".xlsx")):
                continue

            src_file = os.path.join(src_folder_path, file)

            category = get_category(file)

            # -------- determine destination folder --------
            if category == "SC":
                dest_table = f"{folder}_(SC)"
            elif category == "ST":
                dest_table = f"{folder}_(ST)"
            else:
                dest_table = folder

            dest_folder = os.path.join(DEST_ROOT, dest_table)
            os.makedirs(dest_folder, exist_ok=True)

            # -------- FIX FILENAME (IMPORTANT) --------
            state_name = clean_state_name(file)

            new_filename = f"{dest_table}_{state_name}.xls"

            dest_path = os.path.join(dest_folder, new_filename)

            print(f"→ {file}  →  {dest_table}/{new_filename}")

            shutil.copy(src_file, dest_path)

    print("\n✅ Done! Fully 2011-compatible structure created.")


if __name__ == "__main__":
    main()