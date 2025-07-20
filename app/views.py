import logging
import smtplib
import dns.resolver
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from django.http import HttpResponse

def resolve_mx(domain):
    answers = dns.resolver.resolve(domain, 'MX')
    mx = sorted(
        [(r.preference, str(r.exchange).rstrip('.')) for r in answers],
        key=lambda x: x[0]
    )
    return [host for _, host in mx]

def build_message(from_addr, to_addrs, subject, body, helo_domain, user_ip=None):
    msg = EmailMessage()
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=helo_domain)
    msg['MIME-Version'] = '1.0'
    if user_ip:
        msg['X-User-IP'] = user_ip  # ✅ Custom header
        body = f"📡 Visitor IP: {user_ip}\n\n" + body  # ✅ Add IP to body
    msg.set_content(body)
    return msg

def send_news(to_addrs, from_addr, helo_domain, subject, body, no_tls, user_ip=None):
    domain = to_addrs[0].split('@',1)[1]
    mx_hosts = resolve_mx(domain)
    logging.info(f"MX résolus: {mx_hosts}")

    msg = build_message(from_addr, to_addrs, subject, body, helo_domain, user_ip)

    for mx in mx_hosts:
        try:
            logging.info(f"→ Connexion à {mx}")
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"💡 Outbound IP used for SMTP: {local_ip}")

            server = smtplib.SMTP(mx, 25, timeout=10)
            server.ehlo(helo_domain)
            if not no_tls and server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo(helo_domain)
                logging.info("  • STARTTLS activé")

            server.send_message(msg)  # ✅ Send the email
            server.quit()
            logging.info("✅ Envoi réussi via %s", mx)
            return True
        except Exception as e:
            logging.warning("  ✗ Échec sur %s: %s", mx, e)
    logging.error("Tous les MX ont rejeté l'envoi.")
    return False

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def trigger_email(request):
    user_ip = get_client_ip(request)  # ✅ Extract client IP from request

    to_addrs = ["hcodetest@proton.me"]
    from_addr = "newsletter@mail.secret.example"
    helo_domain = "mail.secret.example"
    subject = "Offre Ultra Secrète ! 🚀"
    body = "Ceci est le corps du message envoyé automatiquement par Django."
    no_tls = False

    success = send_news(
        to_addrs=to_addrs,
        from_addr=from_addr,
        helo_domain=helo_domain,
        subject=subject,
        body=body,
        no_tls=no_tls,
        user_ip=user_ip  # ✅ Pass IP here
    )

    if success:
        return HttpResponse("Email sent!", status=200)
    else:
        return HttpResponse("Failed to send email.", status=500)
