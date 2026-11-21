from app.marketplace.providers.partner_stub import PartnerAccessStub


class WishbeeProvider(PartnerAccessStub):
    code = "wishbee"
    name = "Wishbee"
    category = "b2b_wholesale"
    notes = "Wishbee partner credentials required. No unauthorized catalogue access."
