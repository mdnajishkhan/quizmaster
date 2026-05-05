from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def indian_currency(value):
    if value is None:
        return ""
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value
        
    value = str(value)
    if len(value) <= 3:
        return value
        
    last_three = value[-3:]
    remaining = value[:-3]
    
    # regex to split into pairs
    import re
    pairs = re.findall(r'.{1,2}', remaining[::-1])
    formatted_remaining = ",".join(pairs)[::-1]
    
    return formatted_remaining + "," + last_three
    
@register.filter
def whatsapp_format(value):
    """
    Formats a phone number for WhatsApp URL.
    - Removes non-digits.
    - If 10 digits (India), prepends 91.
    - Handles +91 or 0 prefix.
    """
    if not value: return ""
    import re
    # Keep only digits
    clean = re.sub(r'\D', '', str(value))
    
    # Logic for India (common case)
    if len(clean) == 10:
        return '91' + clean
    elif len(clean) == 11 and clean.startswith('0'):
        return '91' + clean[1:]
    elif len(clean) == 12 and clean.startswith('91'):
        return clean
    
    # Fallback: If length is less than 10, it's likely invalid for international WhatsApp
    if len(clean) < 10:
        return ""
        
    # Else return whatever digits (international support)
    return clean
