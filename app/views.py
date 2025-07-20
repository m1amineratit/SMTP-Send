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

def build_message(from_addr, to_addrs, subject, body, helo_domain):
    msg = EmailMessage()
    msg['From']        = from_addr
    msg['To']          = ', '.join(to_addrs)
    msg['Subject']     = subject
    msg['Date']        = formatdate(localtime=True)
    msg['Message-ID']  = make_msgid(domain=helo_domain)
    msg['MIME-Version']= '1.0'
    msg.set_content(body)
    return msg

def send_news(to_addrs, from_addr, helo_domain, subject, body, no_tls):
    domain = to_addrs[0].split('@',1)[1]
    mx_hosts = resolve_mx(domain)
    logging.info(f"MX résolus: {mx_hosts}")

    msg = build_message(from_addr, to_addrs, subject, body, helo_domain)

    for mx in mx_hosts:
        try:
            logging.info(f"→ Connexion à {mx}")
            server = smtplib.SMTP(mx, 25, timeout=10)
            server.ehlo(helo_domain)
            if not no_tls and server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo(helo_domain)
                logging.info("  • STARTTLS activé")
            server.send_message(msg)
            server.quit()
            logging.info("✅ Envoi réussi via %s", mx)
            return True
        except Exception as e:
            logging.warning("  ✗ Échec sur %s: %s", mx, e)
    logging.error("Tous les MX ont rejeté l'envoi.")
    return False

def trigger_email(request):
    # Static/fixed values (replace with your own)
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
        no_tls=no_tls
    )
    if success:
        return HttpResponse("Email sent!", status=200)
    else:
        return HttpResponse("Failed to send email.", status=500)