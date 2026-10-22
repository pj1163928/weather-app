from django import template

register = template.Library()


@register.inclusion_tag("weather/_save_place.html", takes_context=True)
def save_place(context):
    from weather.views import _save_place_context

    data = _save_place_context(context["request"], context, oob=False)
    data["csrf_token"] = context.get("csrf_token")
    return data
