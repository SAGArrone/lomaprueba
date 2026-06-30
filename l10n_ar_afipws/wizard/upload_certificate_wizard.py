##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models
import base64


class L10nArAfipwsUploadCertificate(models.TransientModel):
    _name = "afipws.upload_certificate.wizard"
    _description = "afipws.upload_certificate.wizard"

    @api.model
    def get_certificate(self):
        return self.env["afipws.certificate"].browse(self._context.get("active_id"))

    certificate_id = fields.Many2one(
        "afipws.certificate",
        required=True,
        readonly=True,
        default=get_certificate,
        ondelete="cascade",
    )
    certificate_file = fields.Binary("Upload Certificate", required=True)

    def action_confirm(self):
        """ """
        self.ensure_one()
        certificate_file = self.certificate_file
        if isinstance(certificate_file, str):
            certificate_file = certificate_file.encode("ascii")
        certificate = base64.b64decode(certificate_file).decode("utf-8")
        self.certificate_id.write({"crt": certificate})
        self.certificate_id.action_confirm()
        return True
