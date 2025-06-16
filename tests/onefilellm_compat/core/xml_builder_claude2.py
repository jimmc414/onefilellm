"""XML builder compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import escape_xml

def combine_xml_outputs(outputs):
    """Combine multiple XML outputs into one"""
    if not outputs:
        return "<onefilellm_output></onefilellm_output>"
    
    combined = ["<onefilellm_output>"]
    for output in outputs:
        # Strip the outer onefilellm_output tags if present
        content = output
        if content.startswith("<onefilellm_output>"):
            content = content.replace("<onefilellm_output>", "").replace("</onefilellm_output>", "")
        combined.append(content)
    combined.append("</onefilellm_output>")
    return "\n".join(combined)

def create_source_element(source_type, **attributes):
    """Create a source XML element"""
    attrs = " ".join([f'{k}="{escape_xml(str(v))}"' for k, v in attributes.items()])
    return f'<source type="{escape_xml(source_type)}" {attrs}>'

def create_file_element(path, content):
    """Create a file XML element"""
    return f'<file path="{escape_xml(path)}">\n{content}\n</file>'

def create_error_element(error_msg):
    """Create an error XML element"""
    return f'<error>{escape_xml(error_msg)}</error>'