from app.marketplace.providers.partner_stub import PartnerAccessStub


class UdaanProvider(PartnerAccessStub):
    code = "udaan"
    name = "Udaan"
    category = "b2b_wholesale"
    notes = "Udaan seller/buyer partner integration required for live offers."
