
from PIL import Image
from cStringIO import StringIO
from AccessControl import ClassSecurityInfo
from Products.Archetypes.Field import ImageField
from Products.Archetypes.Widget import ImageWidget
from Products.Archetypes.Registry import registerField

class WatermarkImageField(ImageField):
    """sends image uploaded to imagemagick for pre-treatment, especially watermarking.
    """
    _properties = ImageField._properties.copy()
    _properties.update({
        'watermark': None,
        'watermark_position': 'bottom_right',
    })

    security = ClassSecurityInfo()

    security.declarePrivate('set')
    def set(self, instance, value, **kwargs):
        if not value:
            return
        # Do we have to delete the image?
        if value=="DELETE_IMAGE":
            self.removeScales(instance, **kwargs)
            # unset main field too
            ObjectField.unset(self, instance, **kwargs)
            return

        kwargs.setdefault('mimetype', None)
        default = self.getDefault(instance)
        value, mimetype, filename = self._process_input(value, default=default,
                                                        instance=instance, **kwargs)
        # value is an OFS.Image.File based instance
        # don't store empty images
        get_size = getattr(value, 'get_size', None)
        if get_size is not None and get_size() == 0:
            return
        
        kwargs['mimetype'] = mimetype
        kwargs['filename'] = filename

        try:
            data = self.rescaleOriginal(value, **kwargs)
        except (ConflictError, KeyboardInterrupt):
            raise
        except:
            if not self.swallowResizeExceptions:
                raise
            else:
                log_exc()
                data = str(value.data)

      
        # WATERMARK - Adds a watermark to an image
        f_image = StringIO(data)
        image = Image.open(f_image)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        # create a transparent layer the size of the 
        # image and draw the watermark in that layer.
        layer = Image.new('RGBA', image.size, (0,0,0,0))
        mark = Image.open(self.watermark)
        if self.watermark_position == 'bottom_right':
            position = (layer.size[0]-mark.size[0], layer.size[1]-mark.size[1])
            layer.paste(mark, position)
        else: 
            # TODO :: only supports bottom_right option till know.
            raise 'TODO :: only supports bottom_right option till know.'
        image = Image.composite(layer, image, layer)
        f_data = StringIO()
        image.save(f_data, 'jpeg')
        data = f_data.getvalue()
        f_image.close()
        f_data.close()

        # TODO add self.ZCacheable_invalidate() later
        self.createOriginal(instance, data, **kwargs)
        self.createScales(instance, value=data)


registerField(WatermarkImageField,
              title='Watermark Image',
              description='A field that watermarks images.')
