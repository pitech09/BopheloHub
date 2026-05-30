from django.db import models
from accounts.models import User
from django_ckeditor_5.fields import CKEditor5Field

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_teaching')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    description = CKEditor5Field(config_name='extends')      # CKEditor 5
    thumbnail = models.ImageField(upload_to='courses/thumbnails/')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    