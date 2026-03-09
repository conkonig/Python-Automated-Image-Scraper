import csv
import os

# CONFIG
input_csv = "small_towns.csv"
output_csv = "towns_with_featured_img.csv"

source_column = "city"      # column to read from
new_column = "featured_img" # column to create
suffix = ".jpeg"            # what to append
images_dir = "downloaded_images"  # folder to verify images exist

with open(input_csv, newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + [new_column]

    rows = []

    for row in reader:
        value = row.get(source_column, "").strip()

        # convert spaces to underscores for filename
        filename_base = value.replace(" ", "_")
        filename = f"{filename_base}{suffix}"

        # check if file exists in downloaded_images folder
        image_path = os.path.join(images_dir, filename)

        if os.path.exists(image_path):
            row[new_column] = filename
        else:
            row[new_column] = ""  # leave blank if image missing

        rows.append(row)

with open(output_csv, "w", newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Done. Output written to {output_csv}")