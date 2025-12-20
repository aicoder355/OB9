import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex to fix the split yesno filter
        # Matches {{ variable| yesno: "true,false" \n }} with various spacing
        pattern = r'\{\{\s*(\w+)\s*\|\s*yesno:\s*"true,false"\s*\}\}'
        # This simple pattern might not catch the multi-line one.
        
        # Let's use a more aggressive pattern for the multi-line mess
        # The bad pattern looks like:
        # {{ can_change_driver| yesno: "true,false"
        #    }};
        
        # We want to replace it with: {{ can_change_driver|yesno:"true,false" }}
        
        # Pattern for can_change_driver
        content = re.sub(
            r'\{\{\s*can_change_driver\s*\|\s*yesno:\s*"true,false"\s*\}\}',
            '{{ can_change_driver|yesno:"true,false" }}',
            content,
            flags=re.DOTALL
        )
        # Handle multi-line specifically if the above didn't catch it
        content = re.sub(
            r'\{\{\s*can_change_driver\s*\|\s*yesno:\s*"true,false"\s*\n\s*\}\}',
            '{{ can_change_driver|yesno:"true,false" }}',
            content,
            flags=re.DOTALL
        )
        
        # Pattern for can_delete_driver
        content = re.sub(
            r'\{\{\s*can_delete_driver\s*\|\s*yesno:\s*"true,false"\s*\}\}',
            '{{ can_delete_driver|yesno:"true,false" }}',
            content,
            flags=re.DOTALL
        )
        
        # Pattern for can_change_client
        content = re.sub(
            r'\{\{\s*can_change_client\s*\|\s*yesno:\s*"true,false"\s*\}\}',
            '{{ can_change_client|yesno:"true,false" }}',
            content,
            flags=re.DOTALL
        )
        # Handle multi-line specifically
        content = re.sub(
            r'\{\{\s*can_change_client\s*\|\s*yesno:\s*"true,false"\s*\n\s*\}\}',
            '{{ can_change_client|yesno:"true,false" }}',
            content,
            flags=re.DOTALL
        )

        # Pattern for can_delete_client
        content = re.sub(
            r'\{\{\s*can_delete_client\s*\|\s*yesno:\s*"true,false"\s*\}\}',
            '{{ can_delete_client|yesno:"true,false" }}',
            content,
            flags=re.DOTALL
        )

        # General cleanup for any remaining spaces in yesno
        content = re.sub(r'\|\s*yesno:\s*"', '|yesno:"', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")
        
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

fix_file('templates/drivers.html')
fix_file('templates/clients.html')
