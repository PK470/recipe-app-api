"""
Serializer for Recipe API
"""
from rest_framework import serializers

from core.models import Recipe, Tag, Ingredient


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for Ingredient object"""

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']
        


class TagSerializer(serializers.ModelSerializer):
    """serializer for tag"""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for Recipe object"""
    tags = TagSerializer(many = True, required = False)
    ingredient = IngredientSerializer(many = True, required = False)

    class Meta:
        model = Recipe
        fields = ['id','title','time_minutes','price','link', 'tags',
                  'ingredient',
        ]
        read_only_fields = ['id']

    def _get_or_create_ingredients(self, ingredients, recipe):
        """Helper method to get or create existing ingredients"""
        auth_user = self.context['request'].user
        for ingredient in ingredients:
            ingredient_obj, created = Ingredient.objects.get_or_create(
                user = auth_user,
                **ingredient
            )
            recipe.ingredient.add(ingredient_obj)

        return recipe
         

    def _get_or_create_tags(self, tags, recipe):
        """handle getting or creating tags as needed."""
        auth_user =  self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user = auth_user, 
                **tag
            )
            recipe.tags.add(tag_obj)

    def create(self,validated_data):
        """creating a recipe"""
        tags = validated_data.pop('tags', [])
        ingredient = validated_data.pop('ingredient', [])
        recipe = Recipe.objects.create(**validated_data)
        
        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingredients(ingredient, recipe)
        return recipe
    
    def update(self, instance, validated_data):
        """update a recipe"""
        tags = validated_data.pop('tags', [])
        ingredient = validated_data.pop('ingredient', [])
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)
        if ingredient is not None:
            instance.ingredient.clear()
            self._get_or_create_ingredients(ingredient, instance)
        
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance



class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for Recipe detail"""
     
    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']
       

class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to recipe"""
    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image':{'required':'True'}}
