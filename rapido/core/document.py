from zope.interface import implements

from .interfaces import IDocument


class Document(object):
    implements(IDocument)

    def __init__(self, context):
        self.context = context
        self.uid = self.context.uid()
        self.id = self.context.get_item('docid')
        self.app = self.context.app
        form_id = self.get_item('Form')
        if form_id:
            self.form = self.app.get_form(form_id)
        else:
            self.form = None

    @property
    def url(self):
        return '/'.join([
            self.app.url,
            "document",
            str(self.id),
        ])

    @property
    def title(self):
        return self.get_item('title')

    def set_item(self, name, value):
        if name == "docid":
            # make sure id is unique
            duplicate = self.app.get_document(value)
            if duplicate and duplicate.uid != self.uid:
                value = "%s-%s" % (value, str(hash(self.context)))
            self.id = value
        self.context.set_item(name, value)

    def get_item(self, name, default=None):
        if self.context.has_item(name):
            return self.context.get_item(name)
        else:
            return default

    def remove_item(self, name):
        self.context.remove_item(name)

    def items(self):
        return self.context.items()

    def reindex(self):
        self.app.reindex(self)

    def save(self, request=None, form=None, form_id=None, creation=False):
        """ Update the document with the provided items.
        Request can be an actual HTTP request or a dictionnary.
        If a form is mentionned, formulas will be executed.
        If no form (and request is a dict), we just save the items values.
        """
        if not(form or form_id or (request and request.get('Form'))):
            if type(request) is dict:
                for (key, value) in request.items():
                    self.set_item(key, value)
                self.reindex()
                return
            else:
                raise Exception("Cannot save without a form")
        if not form_id and request:
            form_id = request.get('Form')
        if not form:
            form = self.app.get_form(form_id)
        self.set_item('Form', form.id)

        # store submitted fields
        if request:
            for field in form.fields.keys():
                if field in request.keys():
                    self.set_item(field, request.get(field))

        # compute fields
        for (field, params) in form.fields.items():
            if (params.get('mode') == 'COMPUTED_ON_SAVE' or
                (params.get('mode') == 'COMPUTED_ON_CREATION' and creation)):
                self.set_item(
                    field, form.compute_field(field, {'document': self}))

        # compute id if doc creation
        if creation:
            docid = form.execute('doc_id', self)
            if docid:
                self.set_item('docid', docid)

        # execute on_save
        form.on_save(self)

        # compute title
        title = form.compute_field('title', {'document': self})
        if not title:
            title = form.title
        self.set_item('title', title)

        self.reindex()

    def display(self, edit=False):
        if self.form:
            return self.form.display(doc=self, edit=edit)
