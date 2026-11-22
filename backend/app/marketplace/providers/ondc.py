from app.marketplace.providers.partner_stub import PartnerAccessStub


class OndcProvider(PartnerAccessStub):
    code = "ondc"
    name = "ONDC Retail Grocery (RET10)"
    category = "open_commerce"
    notes = (
        "ONDC network participant onboarding required (subscriber ID, crypto keys, "
        "gateway registration). Implement per official ONDC protocol — not assumed here."
    )
