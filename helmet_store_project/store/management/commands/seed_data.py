from django.core.management.base import BaseCommand
from store.models import Category, Brand, Helmet

class Command(BaseCommand):
    help = 'Seed database with sample helmet data'

    def handle(self, *args, **kwargs):
        Category.objects.all().delete()
        Brand.objects.all().delete()
        Helmet.objects.all().delete()
        
        categories = {
            'street': Category.objects.create(name='Street Helmets', slug='street', description='Perfect for daily commuting and urban riding'),
            'sport': Category.objects.create(name='Sport Helmets', slug='sport', description='Designed for high-speed performance'),
            'adventure': Category.objects.create(name='Adventure Helmets', slug='adventure', description='For touring and off-road adventures'),
        }
        
        brands = {
            'shoei': Brand.objects.create(name='SHOEI', slug='shoei'),
            'arai': Brand.objects.create(name='ARAI', slug='arai'),
            'agv': Brand.objects.create(name='AGV', slug='agv'),
            'bell': Brand.objects.create(name='Bell', slug='bell'),
            'ls2': Brand.objects.create(name='LS2', slug='ls2'),
            'hjc': Brand.objects.create(name='HJC', slug='hjc'),
        }
        
        helmets_data = [
            {'name': 'NXR2', 'brand': 'shoei', 'cat': 'sport', 'type': 'full_face', 'price': 599.99, 'size': 'M', 'color': 'Matte Black', 'material': 'AIM+ Composite', 'cert': 'ece', 'stock': 15, 'featured': True, 'desc': 'Premium full-face helmet with advanced ventilation and aerodynamics.'},
            {'name': 'RX-7V', 'brand': 'arai', 'cat': 'sport', 'type': 'full_face', 'price': 799.99, 'size': 'L', 'color': 'White', 'material': 'Super Fiber', 'cert': 'snell', 'stock': 8, 'featured': True, 'desc': 'Top-tier racing helmet with round shell design for maximum safety.'},
            {'name': 'K6', 'brand': 'agv', 'cat': 'sport', 'type': 'full_face', 'price': 449.99, 'size': 'M', 'color': 'Red/Black', 'material': 'Carbon-Aramid', 'cert': 'ece', 'stock': 20, 'featured': True, 'desc': 'Ultra-lightweight sport helmet with 4-density EPS.'},
            {'name': 'Star DLX', 'brand': 'bell', 'cat': 'street', 'type': 'full_face', 'price': 349.99, 'size': 'L', 'color': 'Blue', 'material': 'Fiberglass', 'cert': 'dot', 'stock': 12, 'featured': False, 'desc': 'Classic American styling with modern protection.'},
            {'name': 'Challenger', 'brand': 'ls2', 'cat': 'street', 'type': 'full_face', 'price': 199.99, 'size': 'XL', 'color': 'Gloss Black', 'material': 'KPA', 'cert': 'ece', 'stock': 25, 'featured': False, 'desc': 'Affordable full-face with drop-down sun visor.'},
            {'name': 'i90', 'brand': 'hjc', 'cat': 'street', 'type': 'modular', 'price': 249.99, 'size': 'M', 'color': 'Silver', 'material': 'Polycarbonate', 'cert': 'dot', 'stock': 18, 'featured': False, 'desc': 'Versatile modular helmet perfect for touring riders.'},
            {'name': 'Neotec II', 'brand': 'shoei', 'cat': 'adventure', 'type': 'modular', 'price': 699.99, 'size': 'L', 'color': 'Anthracite', 'material': 'AIM', 'cert': 'dot', 'stock': 10, 'featured': True, 'desc': 'Premium modular helmet with integrated sun shield.'},
            {'name': 'Tour-X4', 'brand': 'arai', 'cat': 'adventure', 'type': 'dual_sport', 'price': 649.99, 'size': 'M', 'color': 'Orange', 'material': 'Super Fiber', 'cert': 'snell', 'stock': 7, 'featured': False, 'desc': 'Dual-sport helmet with peak visor and wide viewport.'},
            {'name': 'AX-9', 'brand': 'agv', 'cat': 'adventure', 'type': 'dual_sport', 'price': 499.99, 'size': 'L', 'color': 'Sand', 'material': 'Carbon-Fiberglass', 'cert': 'ece', 'stock': 14, 'featured': False, 'desc': 'Adventure touring helmet with extreme ventilation.'},
            {'name': 'Eliminator', 'brand': 'bell', 'cat': 'street', 'type': 'open_face', 'price': 299.99, 'size': 'M', 'color': 'Matte Green', 'material': 'Fiberglass', 'cert': 'dot', 'stock': 16, 'featured': False, 'desc': 'Retro-styled open face with modern safety features.'},
            {'name': 'OF562', 'brand': 'ls2', 'cat': 'street', 'type': 'open_face', 'price': 79.99, 'size': 'S', 'color': 'White', 'material': 'HPTT', 'cert': 'ece', 'stock': 30, 'featured': False, 'desc': 'Budget-friendly open face helmet with sun visor.'},
            {'name': 'FG-17', 'brand': 'hjc', 'cat': 'sport', 'type': 'full_face', 'price': 179.99, 'size': 'XL', 'color': 'Yellow', 'material': 'Fiberglass', 'cert': 'snell', 'stock': 22, 'featured': False, 'desc': 'Entry-level sport helmet with premium features.'},
        ]
        
        for h in helmets_data:
            Helmet.objects.create(
                name=h['name'],
                brand=brands[h['brand']],
                category=categories[h['cat']],
                slug=f"{h['brand']}-{h['name']}".lower().replace(' ', '-'),
                description=h['desc'],
                price=h['price'],
                helmet_type=h['type'],
                size=h['size'],
                color=h['color'],
                material=h['material'],
                certification=h['cert'],
                stock=h['stock'],
                is_featured=h['featured'],
                weight=1.4,
                ventilation=True,
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded 12 helmets!'))