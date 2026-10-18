"""Fluxo e regras de categorias."""
from models.category import DEFAULT_COLOR, Category
from utils.exceptions import NotFoundError, ValidationError
from utils.validators import require_payload, validate_color


class CategoryController:
    def list_categories(self):
        result = []
        for category, task_count in Category.list_with_task_count():
            data = category.to_dict()
            data["task_count"] = task_count
            result.append(data)
        return result

    def create_category(self, data):
        require_payload(data)
        name = data.get("name")
        if not name:
            raise ValidationError("Nome é obrigatório")

        category = Category(
            name=name,
            description=data.get("description", ""),
            color=validate_color(data.get("color", DEFAULT_COLOR)),
        )
        return category.save().to_dict()

    def update_category(self, category_id, data):
        category = self._get_or_404(category_id)
        require_payload(data)
        if "name" in data and not data["name"]:
            raise ValidationError("Nome é obrigatório")
        if "color" in data:
            validate_color(data["color"])

        for field in ("name", "description", "color"):
            if field in data:
                setattr(category, field, data[field])
        return category.save().to_dict()

    def delete_category(self, category_id):
        # As tasks da categoria são desassociadas (category_id = NULL) pelo relacionamento.
        self._get_or_404(category_id).delete()

    @staticmethod
    def _get_or_404(category_id):
        category = Category.get(category_id)
        if not category:
            raise NotFoundError("Categoria não encontrada")
        return category
