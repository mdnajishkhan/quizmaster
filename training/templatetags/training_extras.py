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
    
    return f"{formatted_remaining},{last_three}"
