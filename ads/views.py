from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, OuterRef, Subquery
from django.contrib.humanize.templatetags.humanize import naturaltime

from ads.forms import CreateForm, CommentForm
from ads.models import Ad, Comment, Fav
from ads.owner import OwnerListView, OwnerDetailView, OwnerDeleteView


class AdListView(OwnerListView):
    model = Ad
    template_name = "ads/ad_list.html"

    def get_queryset(self, search_query=None):
        """
        Fetch ads based on a search query or return the most recent ads.
        """
        if search_query:
            query = Q(title__icontains=search_query)
            query.add(Q(text__icontains=search_query), Q.OR)
            query.add(Q(tags__name__in=[search_query]), Q.OR)
            return Ad.objects.filter(query).select_related().distinct().order_by('-updated_at')[:10]
        return Ad.objects.all().order_by('-updated_at')[:10]

    def get_favorites(self, user):
        """
        Fetch the IDs of the ads marked as favorites by the user.
        """
        if user.is_authenticated:
            rows = user.favorite_ads.values('id')
            return [row['id'] for row in rows]
        return []

    def get_grouped_tasks(self):
        """
        Group tasks (ads) by the responsible user's username and sort them by the last comment time.
        """
        grouped_tasks = defaultdict(list)
        latest_comment = Comment.objects.filter(ad=OuterRef('pk')).order_by('-updated_at')
        tasks = Ad.objects.annotate(
            last_comment_time=Subquery(latest_comment.values('updated_at')[:1]),
            last_comment_content=Subquery(latest_comment.values('text')[:1]),
            last_comment_owner=Subquery(latest_comment.values('owner__username')[:1])
        ).order_by('-last_comment_time')

        for task in tasks:
            grouped_tasks[task.responsible.username].append(task)
        return grouped_tasks

    def augment_ads(self, ads):
        """
        Add a human-readable timestamp (natural time) to each ad.
        """
        for ad in ads:
            ad.natural_updated = naturaltime(ad.updated_at)

    def get(self, request):
        """
        Handle GET requests and render the ad list view.
        """
        search_query = request.GET.get("search", False)
        ad_list = self.get_queryset(search_query)
        self.augment_ads(ad_list)
        favorites = self.get_favorites(request.user)
        grouped_tasks = self.get_grouped_tasks()

        ctx = {
            'ad_list': ad_list,
            'favorites': favorites,
            'search': search_query,
            'grouped_tasks': dict(grouped_tasks),  # Convert defaultdict to a regular dictionary
        }
        return render(request, self.template_name, ctx)


class AdDetailView(OwnerDetailView):
    model = Ad
    template_name = "ads/ad_detail.html"
    #fields = ['title','price','text','tags','comments']
    def get(self, request, pk) :
        x = get_object_or_404(Ad, id=pk)
        comments = Comment.objects.filter(ad=x).order_by('-updated_at')
        comment_form = CommentForm()
        context = { 'ad' : x, 'comments': comments, 'comment_form': comment_form }
        return render(request, self.template_name, context)

class AdCreateView(LoginRequiredMixin, View):
    template_name = 'ads/ad_form.html'
    success_url = reverse_lazy('ads:all')

    def get(self, request, pk=None):
        form = CreateForm()
        ctx = {'form': form}
        return render(request, self.template_name, ctx)

    def post(self, request, pk=None):
        form = CreateForm(request.POST, request.FILES or None)

        if not form.is_valid():
            ctx = {'form': form}
            return render(request, self.template_name, ctx)

        # Add owner to the model before saving
        pic = form.save(commit=False)
        pic.owner = self.request.user
        pic.save()
        form.save_m2m()

        return redirect(self.success_url)

class AdUpdateView(LoginRequiredMixin, View):
    template_name = 'ads/ad_form.html'
    success_url = reverse_lazy('ads:all')

    def get(self, request, pk):
        pic = get_object_or_404(Ad, id=pk, owner=self.request.user)
        form = CreateForm(instance=pic)
        ctx = {'form': form}
        return render(request, self.template_name, ctx)

    def post(self, request, pk=None):
        pic = get_object_or_404(Ad, id=pk, owner=self.request.user)
        form = CreateForm(request.POST, request.FILES or None, instance=pic)

        if not form.is_valid():
            ctx = {'form': form}
            return render(request, self.template_name, ctx)

        pic = form.save(commit=False)
        pic.save()
        form.save_m2m()

        return redirect(self.success_url)


class AdDeleteView(OwnerDeleteView):
    model = Ad
    fields = ['title','price','tags','text']

class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk) :
        f = get_object_or_404(Ad, id=pk)
        comment = Comment(text=request.POST['comment'], owner=request.user, ad=f)
        comment.save()
        return redirect(reverse('ads:ad_detail', args=[pk]))

class CommentDeleteView(OwnerDeleteView):
    model = Comment
    template_name = "ads/comment_delete.html"

def stream_file(request, pk):
    pic = get_object_or_404(Ad, id=pk)
    response = HttpResponse()
    response['Content-Type'] = pic.content_type
    response['Content-Length'] = len(pic.picture)
    response.write(pic.picture)
    return response

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.utils import IntegrityError

@method_decorator(csrf_exempt, name='dispatch')
class AddFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk) :
        t = get_object_or_404(Ad, id=pk)
        fav = Fav(user=request.user, ad=t)
        try:
            fav.save()  # In case of duplicate key
        except IntegrityError:
            pass
        return HttpResponse("Favorite added 42")

@method_decorator(csrf_exempt, name='dispatch')
class DeleteFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk) :
        t = get_object_or_404(Ad, id=pk)
        try:
            Fav.objects.get(user=request.user, ad=t).delete()
        except Fav.DoesNotExist:
            pass

        return HttpResponse("Favorite deleted 42")