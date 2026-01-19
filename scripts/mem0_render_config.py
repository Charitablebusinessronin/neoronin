#!/usr/bin/env python3
"""
Render mem0_config.yaml from template using environment variables.
This script replaces ${VAR} placeholders with actual environment variable values.
"""

import os
import sys
import re

def render_template(template_path, output_path):
    """Render template file with environment variable substitution."""
    try:
        with open(template_path, 'r') as f:
            template = f.read()
        
        # Replace ${VAR} with environment variable values
        def replace_var(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) else None
            value = os.getenv(var_name, default)
            if value is None:
                raise ValueError(f"Environment variable {var_name} is not set and no default provided")
            return value
        
        # Pattern: ${VAR} or ${VAR:-default}
        pattern = r'\$\{([^:}]+)(?::-([^}]+))?\}'
        rendered = re.sub(pattern, replace_var, template)
        
        with open(output_path, 'w') as f:
            f.write(rendered)
        
        print(f"✅ Rendered config: {template_path} -> {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to render config: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    template_path = "/app/config/mem0_config.yaml.template"
    output_path = "/app/config/mem0_config.yaml"
    
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)
    
    success = render_template(template_path, output_path)
    sys.exit(0 if success else 1)




