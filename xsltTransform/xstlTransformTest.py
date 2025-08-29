import sys
from lxml import etree

def transform_xml(xml_file, xslt_file, output_file):
    """
    Transforms an XML document using an XSLT stylesheet.

    Args:
        xml_file (str): The path to the input XML file.
        xslt_file (str): The path to the XSLT stylesheet file.
        output_file (str): The path to the output file (XML, HTML, or text).
    """
    try:
        # 1. Load the XML and XSLT files
        print(f"Loading XML from: {xml_file}")
        xml_tree = etree.parse(xml_file)
        
        print(f"Loading XSLT from: {xslt_file}")
        xslt_tree = etree.parse(xslt_file)
        
        # 2. Create the XSLT transformer
        transformer = etree.XSLT(xslt_tree)
        
        # 3. Perform the transformation
        print("Performing transformation...")
        result_tree = transformer(xml_tree)
        
        # 4. Save the result to the output file
        with open(output_file, 'wb') as f:
            f.write(etree.tostring(result_tree, pretty_print=True))
            
        print(f"Transformation complete. Output saved to: {output_file}")
        
    except etree.XMLSyntaxError as e:
        print(f"Error parsing XML or XSLT file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: One of the specified files was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check for the correct number of command-line arguments
    if len(sys.argv) != 4:
        print("Usage: python transform.py <input_xml_file> <xslt_stylesheet_file> <output_file>")
        sys.exit(1)
    
    input_xml = sys.argv[1]
    xslt_stylesheet = sys.argv[2]
    output_path = sys.argv[3]
    
    transform_xml(input_xml, xslt_stylesheet, output_path)