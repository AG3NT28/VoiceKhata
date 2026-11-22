from app.marketplace.providers.partner_stub import PartnerAccessStub


class JumbotailProvider(PartnerAccessStub):
    code = "jumbotail"
    name = "Jumbotail"
    category = "b2b_wholesale"
    notes = (
        "Jumbotail B2B partner API / seller portal access required. "
        "Do not scrape. Redirect domains: jumbotail.com once deep links are authorized."
    )
