from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a string key,
    useful for keys that contain special characters.
    """
    return dictionary.get(key, 0)  # Return 0 if key doesn't exist 