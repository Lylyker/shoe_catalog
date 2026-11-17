from django import forms
from django.forms import inlineformset_factory

from catalog.models import MaterialProduct, Product, ProductVariant
from supply.models import Supply, SupplyItem
from users.models import User


def style(form_class):
    """Навешивает классы дизайн-системы на виджеты формы."""
    for field in form_class.base_fields.values():
        w = field.widget
        if isinstance(w, forms.CheckboxInput):
            w.attrs['class'] = 'form-check-input'
        elif isinstance(w, (forms.Select, forms.SelectMultiple)):
            w.attrs['class'] = 'form-select'
        elif isinstance(w, forms.Textarea):
            w.attrs.update({'class': 'form-control', 'rows': 3})
        else:
            w.attrs['class'] = 'form-control'
    return form_class


def build_form(model, fields='__all__', exclude=()):
    return style(forms.modelform_factory(model, fields=fields, exclude=exclude))


class UserForm(forms.ModelForm):
    new_password = forms.CharField(
        label='Новый пароль', required=False, widget=forms.PasswordInput,
        help_text='Оставьте пустым, чтобы не менять. Пользователь будет обязан сменить его при входе.')

    class Meta:
        model = User
        fields = ['login', 'full_name', 'email', 'phone', 'delivery_address', 'gender',
                  'role', 'is_active', 'is_staff', 'is_admin', 'is_superuser']
        widgets = {'delivery_address': forms.Textarea(attrs={'rows': 2})}

    def clean_login(self):
        login = self.cleaned_data['login'].strip()
        qs = User.objects.filter(login__iexact=login)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Пользователь с таким логином уже существует.')
        return login


class SupplyForm(forms.ModelForm):
    class Meta:
        model = Supply
        fields = ['supplier', 'warehouse', 'date_supply', 'note']
        widgets = {'date_supply': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'note': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_supply'].input_formats = ['%Y-%m-%d']


class OrderItemAddForm(forms.Form):
    product_variant = forms.ModelChoiceField(
        label='Вариант товара', queryset=ProductVariant.objects.select_related(
            'product', 'size', 'color').order_by('product__name'))
    quantity = forms.IntegerField(label='Количество', min_value=1, initial=1)
    price_order = forms.DecimalField(label='Цена продажи', max_digits=10, decimal_places=2,
                                     required=False)


class StockAdjustForm(forms.Form):
    delta = forms.IntegerField(label='Изменение (+ приход / − расход)')
    note = forms.CharField(label='Основание', required=False, max_length=200)


VariantFormSet = inlineformset_factory(
    Product, ProductVariant, fields=('size', 'color', 'quantity'), extra=1, can_delete=True)
MaterialFormSet = inlineformset_factory(
    Product, MaterialProduct, fields=('material', 'detail'), extra=1, can_delete=True)
SupplyItemFormSet = inlineformset_factory(
    Supply, SupplyItem, fields=('product_variant', 'quantity', 'purchase_price'),
    extra=2, can_delete=True)