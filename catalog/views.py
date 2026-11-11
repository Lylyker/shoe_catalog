from django.shortcuts import redirect
from django.views.generic import DetailView
from django_filters.views import FilterView
from django.db.models import Sum, Avg
from django.contrib import messages

from .models import Product, ProductVariant, Category, Comment
from .filters import ProductFilter
from .forms import CommentForm


class CatalogView(FilterView):
    """Главная страница каталога с фильтрацией"""
    model = Product
    template_name = 'catalog/catalog.html'
    context_object_name = 'products'
    filterset_class = ProductFilter
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(total_quantity=Sum('variants__quantity'))

        sort = self.request.GET.get('sort', '')
        if sort == 'price_asc':
            queryset = queryset.order_by('retail_price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-retail_price')
        else:
            queryset = queryset.order_by('name')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['sort_options'] = [
            ('', 'По умолчанию'),
            ('price_asc', 'По возрастанию цены'),
            ('price_desc', 'По убыванию цены'),
            ('name', 'По названию'),
        ]
        context['current_sort'] = self.request.GET.get('sort', '')
        return context


class ProductDetailView(DetailView):
    """Карточка товара + отзывы. POST — создание/обновление отзыва."""
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variants'] = ProductVariant.objects.filter(
            product=self.object, quantity__gt=0
        ).select_related('size', 'color')

        comments = self.object.comments.select_related('user', 'user__role').all()
        count = comments.count()
        avg = comments.aggregate(avg=Avg('rating'))['avg'] or 0

        context['comments'] = comments
        context['comments_count'] = count
        context['avg_rating'] = round(avg, 1)
        context['avg_rating_rounded'] = int(round(avg))

        distribution = []
        for stars in range(5, 0, -1):
            c = comments.filter(rating=stars).count()
            distribution.append({
                'stars': stars,
                'count': c,
                'percent': (c / count * 100) if count else 0,
            })
        context['rating_distribution'] = distribution

        user_comment = None
        if self.request.user.is_authenticated:
            user_comment = comments.filter(user=self.request.user).first()
        context['user_comment'] = user_comment

        if user_comment:
            context['comment_form'] = CommentForm(initial={
                'rating': user_comment.rating,
                'description': user_comment.description,
            })
        else:
            context['comment_form'] = CommentForm(initial={'rating': 5})
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите в систему, чтобы оставить отзыв.')
            return redirect('users:login')

        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.update_or_create(
                product=self.object,
                user=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'description': form.cleaned_data['description'],
                },
            )
            messages.success(request, 'Спасибо! Ваш отзыв сохранён.')
            return redirect(request.path + '#reviews')

        context = self.get_context_data()
        context['comment_form'] = form
        return self.render_to_response(context)