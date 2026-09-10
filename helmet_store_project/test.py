from store.models import Helmet
from django.core.files import File

# Get the first helmet (or any helmet)
h = Helmet.objects.first()

# Open the local image
with open('test.jpg', 'rb') as f:
    h.image.save('test_image.jpg', File(f), save=True)

# Verify
print(h.image)      # Should show the path, e.g., 'helmets/2026/08/test_image.jpg'
print(h.image.url)  # Should show '/media/helmets/2026/08/test_image.jpg'