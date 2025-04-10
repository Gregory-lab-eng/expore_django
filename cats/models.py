from django.db import models
from django.core.validators import MinLengthValidator


class Breed(models.Model):
    name = models.CharField(
            max_length=200,
            help_text='Enter a breed (e.g. Siberian)',
            validators=[MinLengthValidator(2, "Make must be greater than 1 character")]
    )

    def __str__(self):
        """String for representing the Model object."""
        return self.name


class Cat(models.Model):
    nickname = models.CharField(
            max_length=200,
            validators=[MinLengthValidator(2, "Nickname must be greater than 1 character")]
    )
    foods = models.CharField(max_length=300)
    weight = models.CharField(max_length=300)
    breed = models.ForeignKey('Breed', on_delete=models.CASCADE, null=False)

    # Shows up in the admin list
    def __str__(self):
        return self.nickname
