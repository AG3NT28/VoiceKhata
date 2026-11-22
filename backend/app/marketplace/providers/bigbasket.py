from app.marketplace.providers.partner_stub import PartnerAccessStub


class BigBasketProvider(PartnerAccessStub):
    code = "bigbasket"
    name = "BigBasket"
    category = "quick_commerce"
    notes = "BigBasket partner / affiliate access required for authorized redirects."
