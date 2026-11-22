from app.marketplace.providers.partner_stub import PartnerAccessStub


class BlinkitProvider(PartnerAccessStub):
    code = "blinkit"
    name = "Blinkit"
    category = "quick_commerce"
    notes = "Quick-commerce benchmark only when official partner API is available. No scraping."
