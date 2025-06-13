from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_email(subject, to_email, template_name, context={}, from_email=None):
    """
    Envia um e-mail com template HTML e versão em texto.

    - `subject`: assunto do e-mail
    - `to_email`: string ou lista de destinatários
    - `template_name`: nome do template HTML (ex: 'emails/bem_vindo.html')
    - `context`: dicionário com variáveis do template
    - `from_email`: opcional; se não informado usa DEFAULT_FROM_EMAIL
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    if isinstance(to_email, str):
        to_email = [to_email]

    html_content = render_to_string(template_name, context)
    text_content = render_to_string(template_name.replace('.html', '.txt'), context)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
