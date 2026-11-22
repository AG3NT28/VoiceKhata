from app.marketplace.providers.partner_stub import PartnerAccessStub


class JioMartProvider(PartnerAccessStub):
    code = "jiomart"
    name = "JioMart"
    category = "quick_commerce"
    notes = "JioMart partner API access required. Used as price benchmark when authorized."
