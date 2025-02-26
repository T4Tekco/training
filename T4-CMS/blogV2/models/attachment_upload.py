from odoo import models, api, fields, _
import logging
import base64
import pytz # Import thư viện `pytz` để làm việc với múi giờ.
from datetime import datetime, timedelta
from ..controllers.create_blog import BlogController
from odoo.http import request

_logger = logging.getLogger(__name__)

class AttachmentUpload(models.Model):
    _name = 'attachment.upload'
    _description = 'Upload Attachment to Server'
 
    local_attachment_id = fields.Many2one('ir.attachment',
                                            string='Local Attachment',
                                            required=True,
                                            ondelete='cascade')
    
    server_id = fields.Many2one('server', 
                                string='Server',
                                required=True,
                                ondelete='cascade')
    
    def _get_all_blog_transfer(self):
        try:
            blog_transfer = request.env['blog.transfer'].search([])

            if not blog_transfer:
                _logger.info(f"Don't have any blog_transfer {blog_transfer}")
                return None
            
            return blog_transfer
        
        except Exception as e:
            _logger.info(f'Error when get blog_transfer: {e}')
            return None
        
    def _get_attachment_mappings(self, local_attachment_id, server_id): 
        _logger.info('def _get_attachment_mappings')
        try:
            attachment_mapping = request.env['attachment.mapping'].search([
                ('local_attachment_id', '=', local_attachment_id),
                ('server_id', '=', server_id),
                #('server_attachment_id', '=', server_attachment_id)    
            ], limit=1)
            
            if not attachment_mapping:
                _logger.info(f'Not found attachment_mapping with att_local_id: {local_attachment_id} and server_id {server_id}')
            _logger.info(f'attachment_mapping: {attachment_mapping}')
            return attachment_mapping
        
        except Exception as e:
            _logger.error(f"Error getting attachment_mapping: {str(e)}")
            return None
        
    def _get_attachment_uploads(self, local_attachment_id, server_id):
        _logger.info('def _get_attachment_uploads')
        try:
            attachment_uploads = self.env['attachment.upload'].search([
                ('local_attachment_id', '=', local_attachment_id),
                ('server_id', '=', server_id)
            ], limit=1)
            
            if not attachment_uploads:
                _logger.info(f'Not found attachment_uploads with att_local_id: {local_attachment_id} and server_id {server_id}')
            _logger.info(f'attachment_uploads: {attachment_uploads}')
            return attachment_uploads
        
        except Exception as e:
            _logger.error(f"Error getting attachment_uploads: {str(e)}")
            return None

    @api.model
    def process_attachment_transfer_blog(self): # process attachment in all cron-job transfer blog -> return 
        _logger.info('def process_attachment_transfer_blog')
        try:
            blog_transfers = self._get_all_blog_transfer()
            
            if not blog_transfers:
                _logger.info("Don't have any blog_transfer")
                return None
            
            _logger.info(f'Length of blog_transfer {len(blog_transfers)}')

            if blog_transfers:
                for blog_transfer in blog_transfers:
                    posts = blog_transfer.selected_post_id
                    server_id = blog_transfer.server_mapping_id.id
                    _logger.info(f'posts: {posts}')
                    _logger.info(f'server: {server_id}')

                    for post in posts:  
                        attachments = request.env['ir.attachment'].search([
                            ('res_model', '=', 'blog.post'),
                            ('res_id', '=', post.id)
                        ])
                        _logger.info(f'attachments found: {attachments}')
                      
                        if attachments:
                            for attachment in attachments:
                                attachment_id = attachment.id

                                existing_att_mapping = self._get_attachment_mappings(attachment_id, server_id)
                                existing_att_id = existing_att_mapping.local_attachment_id
                                existing_server_id = existing_att_mapping.server_id
                                _logger.info(f'existing_att_id: {existing_att_id}')
                                _logger.info(f'existing_server_id: {existing_server_id}')

                                # if not existing_attachment_mapping
                                if not existing_att_mapping:
                                    new_att_upload = self.env['attachment.upload'].create({
                                        'local_attachment_id': attachment.id,
                                        'server_id': server_id
                                    })
                                    _logger.info(f'New Attachment Upload Created: {new_att_upload}')       

                        _logger.info('DONE')                         
    
        except Exception as e:
            _logger.info(f'Error when process attachment in transfer blog cron-job: {str(e)}')
            return None
        


    @api.model
    def cron_upload_attachments(self):
        _logger.info(f'def cron_upload_attachments')
        blogController = BlogController()

        blogController.get_all_attachment_mapping()
 
        self.process_attachment_transfer_blog()  # Generate new upload records
        attachments_upload_records = self.search([])  # Get all pending upload records
        if attachments_upload_records:
            _logger.info(f'Attachment_upload_record was found with length: {len(attachments_upload_records)}')

        for attachment_upload in attachments_upload_records:
            blogController.upload_attachment(attachment_upload)  # Upload attachments
