from django.views.generic import TemplateView
from django.conf import settings

# Create your views here.

# This is a little complex because we need to detect when we are
# running in various configurations


class HomeView(TemplateView):
    template_name = 'home/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'installed': settings.INSTALLED_APPS,
            'my_statement': "Nice to see you!"
        })
        return context

    def say_welcome(self):
        return 'Welcome'