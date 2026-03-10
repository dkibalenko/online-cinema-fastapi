from jinja2 import Environment, FileSystemLoader, Template


class TemplateRenderer:
    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def get(self, name: str) -> Template:
        """Get a Jinja2 template by name.

        Args:
            name (str): The name of the template to get.

        Returns:
            Template: The requested template.
        """
        return self.env.get_template(name)
