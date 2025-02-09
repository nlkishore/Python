#!/bin/bash

JAR_FILE="example.jar"
OUTPUT_DIR="extracted_classes"
CLASSES_TO_EXTRACT=("com/example/Main.class" "org/example/Service.class")

mkdir -p "$OUTPUT_DIR"

for CLASS in "${CLASSES_TO_EXTRACT[@]}"; do
    unzip -j "$JAR_FILE" "$CLASS" -d "$OUTPUT_DIR/$(dirname $CLASS)"
done

echo "Extraction complete!"
