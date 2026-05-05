from django import template
import hashlib

register = template.Library()

@register.filter
def category_color(value):
    """
    Returns a Tailwind CSS class string based on the hash of the category name.
    Ensures deterministic color assignment (same category = same color).
    """
    if not value:
        return "bg-gray-900/50 text-gray-200 border border-gray-500/30"
    
    colors = [
        "bg-red-900/50 text-red-200 border border-red-500/30",
        "bg-orange-900/50 text-orange-200 border border-orange-500/30",
        "bg-amber-900/50 text-amber-200 border border-amber-500/30",
        "bg-yellow-900/50 text-yellow-200 border border-yellow-500/30",
        "bg-lime-900/50 text-lime-200 border border-lime-500/30",
        "bg-green-900/50 text-green-200 border border-green-500/30",
        "bg-emerald-900/50 text-emerald-200 border border-emerald-500/30",
        "bg-teal-900/50 text-teal-200 border border-teal-500/30",
        "bg-cyan-900/50 text-cyan-200 border border-cyan-500/30",
        "bg-sky-900/50 text-sky-200 border border-sky-500/30",
        "bg-blue-900/50 text-blue-200 border border-blue-500/30",
        "bg-indigo-900/50 text-indigo-200 border border-indigo-500/30",
        "bg-violet-900/50 text-violet-200 border border-violet-500/30",
        "bg-purple-900/50 text-purple-200 border border-purple-500/30",
        "bg-fuchsia-900/50 text-fuchsia-200 border border-fuchsia-500/30",
        "bg-pink-900/50 text-pink-200 border border-pink-500/30",
        "bg-rose-900/50 text-rose-200 border border-rose-500/30",
    ]
    
    # Hash the string to get a consistent integer
    hash_object = hashlib.md5(str(value).encode())
    hash_int = int(hash_object.hexdigest(), 16)
    
    # Pick a color based on the hash
    index = hash_int % len(colors)
    return colors[index]
