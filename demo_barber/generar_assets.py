"""
Script auxiliar para generar assets estáticos iniciales de Demo Barber Club:
- Favicons (ico, 16x16, 32x32, apple-touch-icon)
- Imagen Open Graph 1200x630
- Imágenes WebP optimizadas con diseño editorial para: hero, servicios, barberos, sucursales, galería, productos y blog
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_IMG = os.path.join(BASE_DIR, "static", "img")

COLOR_BG = (10, 10, 10)
COLOR_SURFACE = (22, 22, 22)
COLOR_GOLD = (201, 162, 75)
COLOR_GOLD_LIGHT = (225, 195, 125)
COLOR_IVORY = (245, 240, 230)
COLOR_MUTED = (168, 162, 148)
COLOR_BORDER = (45, 45, 45)

def crear_carpetas():
    subdirs = [
        "logo", "favicon", "hero", "servicios", "barberos",
        "galeria", "productos", "blog", "sucursales", "og"
    ]
    for sub in subdirs:
        os.makedirs(os.path.join(STATIC_IMG, sub), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "video"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "docs", "screenshots"), exist_ok=True)

def generar_favicons():
    # Base 180x180
    size = 180
    img = Image.new("RGBA", (size, size), (10, 10, 10, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([4, 4, size-5, size-5], radius=32, outline=COLOR_GOLD, width=4)
    draw.ellipse([30, 30, size-30, size-30], outline=COLOR_GOLD_LIGHT, width=2)
    # Cruz estilizada
    draw.line([50, 50, size-50, size-50], fill=COLOR_GOLD, width=6)
    draw.line([size-50, 50, 50, size-50], fill=COLOR_GOLD, width=6)
    draw.ellipse([size//2-10, size//2-10, size//2+10, size//2+10], fill=COLOR_GOLD)

    fav_dir = os.path.join(STATIC_IMG, "favicon")
    img.save(os.path.join(fav_dir, "apple-touch-icon.png"), "PNG")
    img.resize((32, 32)).save(os.path.join(fav_dir, "favicon-32x32.png"), "PNG")
    img.resize((16, 16)).save(os.path.join(fav_dir, "favicon-16x16.png"), "PNG")
    img.resize((32, 32)).save(os.path.join(fav_dir, "favicon.ico"), "ICO")
    print("Favicons generados exitosamente.")

def generar_og_image():
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), COLOR_BG)
    draw = ImageDraw.Draw(img)
    # Marco elegante
    draw.rectangle([30, 30, w-30, h-30], outline=COLOR_GOLD, width=2)
    draw.rectangle([45, 45, w-45, h-45], outline=COLOR_BORDER, width=1)
    
    # Dibujar elementos decorativos
    draw.line([w//2 - 120, 180, w//2 + 120, 180], fill=COLOR_GOLD, width=2)
    draw.ellipse([w//2 - 6, 175, w//2 + 6, 187], fill=COLOR_GOLD)
    
    # Texto representativo
    # Usar texto con fuentes por defecto
    draw.text((w//2, 240), "DEMO BARBER CLUB", fill=COLOR_IVORY, anchor="mm")
    draw.text((w//2, 300), "LA EXPERIENCIA DEFINITIVA DE CORTE Y BARBA EN CHILE", fill=COLOR_GOLD, anchor="mm")
    draw.text((w//2, 370), "SISTEMA DE RESERVAS ONLINE • SUCURSALES EN PROVIDENCIA, LAS CONDES Y VITACURA", fill=COLOR_MUTED, anchor="mm")
    draw.text((w//2, 450), "www.demobarberclub.cl", fill=COLOR_GOLD_LIGHT, anchor="mm")
    
    og_path = os.path.join(STATIC_IMG, "og", "og-image.webp")
    img.save(og_path, "WEBP", quality=90)
    print("Imagen Open Graph generada:", og_path)

def generar_placeholder(categoria, nombre, titulo, subtitulo, w=800, h=600):
    img = Image.new("RGB", (w, h), COLOR_SURFACE)
    draw = ImageDraw.Draw(img)
    
    # Marco sutil
    draw.rectangle([15, 15, w-15, h-15], outline=COLOR_BORDER, width=1)
    draw.rectangle([25, 25, w-25, h-25], outline=(30, 30, 30), width=1)
    
    # Emblema central decorativo
    cx, cy = w//2, h//2 - 30
    draw.ellipse([cx-45, cy-45, cx+45, cy+45], outline=COLOR_GOLD, width=2)
    draw.line([cx-25, cy-25, cx+25, cy+25], fill=COLOR_GOLD, width=3)
    draw.line([cx+25, cy-25, cx-25, cy+25], fill=COLOR_GOLD, width=3)
    draw.ellipse([cx-5, cy-5, cx+5, cy+5], fill=COLOR_GOLD)
    
    # Textos
    draw.text((w//2, cy + 80), titulo.upper(), fill=COLOR_IVORY, anchor="mm")
    draw.text((w//2, cy + 115), subtitulo, fill=COLOR_GOLD, anchor="mm")
    draw.text((w//2, h - 45), "DEMO BARBER CLUB — ATELIER DE ESTILO", fill=COLOR_MUTED, anchor="mm")
    
    target = os.path.join(STATIC_IMG, categoria, f"{nombre}.webp")
    img.save(target, "WEBP", quality=85)
    
    # Versión thumb si es necesario
    if w >= 600:
        thumb_target = os.path.join(STATIC_IMG, categoria, f"{nombre}_thumb.webp")
        img.resize((w//2, h//2)).save(thumb_target, "WEBP", quality=80)

def generar_catalogo_demo():
    # Hero
    generar_placeholder("hero", "hero_poster", "Experiencia de Barbería Tradicional & Contemporánea", "Sillones Clásicos • Navaja Caliente • Cuidado Exclusivo", 1920, 1080)
    
    # Sucursales
    sucursales = [
        ("providencia", "Sucursal Providencia", "Av. Providencia 2145 • Metro Los Leones"),
        ("las_condes", "Sucursal Las Condes", "Av. Apoquindo 4800 • Metro Escuela Militar"),
        ("vitacura", "Sucursal Vitacura", "Av. Vitacura 5600 • Alonso de Córdova"),
    ]
    for slug, tit, sub in sucursales:
        generar_placeholder("sucursales", slug, tit, sub, 900, 600)
        
    # Barberos
    barberos = [
        ("matias_silva", "Matías Silva", "Master Barber • Especialista en Fade y Texturas"),
        ("rodrigo_valenzuela", "Rodrigo Valenzuela", "Senior Barber • Afeitado Tradicional y Barba"),
        ("ignacio_castro", "Ignacio Castro", "Stylist Barber • Tijera Clásica y Visagismo"),
        ("diego_morales", "Diego Morales", "Barber Artist • Perfilados y Diseños de Precisión"),
        ("camilo_fuentes", "Camilo Fuentes", "Grooming Specialist • Cuidados y Tratamientos"),
    ]
    for slug, tit, sub in barberos:
        generar_placeholder("barberos", slug, tit, sub, 600, 750)
        
    # Servicios
    servicios = [
        ("corte_clasico", "Corte Clásico & Fade", "Degradado a elección con asesoría de visagismo"),
        ("afeitado_tradicional", "Afeitado Tradicional", "Toallas calientes, navaja japonesa y bálsamo calmante"),
        ("perfilado_barba", "Perfilado y Ritual de Barba", "Esculpido a tijera, navaja y nutrición profunda"),
        ("combo_corte_barba", "Combo Signature: Corte + Barba", "El servicio completo más solicitado"),
        ("corte_nino", "Corte Niño & Joven", "Atención paciente y estilo moderno para jóvenes"),
        ("tratamiento_capilar", "Tratamiento Detox & Masaje", "Exfoliación capilar y nutrición estimulante"),
    ]
    for slug, tit, sub in servicios:
        generar_placeholder("servicios", slug, tit, sub, 700, 500)
        
    # Productos
    productos = [
        ("pomada_mate", "Pomada Fijación Mate 100ml", "Acabado natural con fijación fuerte y aroma amaderado"),
        ("aceite_barba", "Aceite Esencial para Barba 50ml", "Aceite de argán, jojoba y cedro puro"),
        ("balsamo_aftershave", "Bálsamo Aftershave Calmante 120ml", "Aloe vera, hamamelis y sensación refrescante"),
        ("shampoo_fortificante", "Shampoo Capilar & Barba 250ml", "Fórmula sin sulfatos con mentol y biotina"),
        ("cera_brillo", "Cera Clásica Alto Brillo 100ml", "Look clásico peinado hacia atrás resistente al agua"),
        ("cepillo_cerda", "Cepillo de Cerda Natural de Jabalí", "Madera noble pulida a mano para pulir la barba"),
        ("peine_carbono", "Peine Antiestático de Fibra de Carbono", "Dientes finos y anchos de alta resistencia"),
        ("colonia_tabaco_vainilla", "Eau de Parfum Tabaco & Vainilla 100ml", "Fragancia exclusiva de autor para caballeros"),
    ]
    for slug, tit, sub in productos:
        generar_placeholder("productos", slug, tit, sub, 700, 700)
        
    # Galería
    galeria = [
        ("galeria_1", "Skin Fade de Alta Precisión", "Transición limpia y perfilado de patillas"),
        ("galeria_2", "Barba Esculpida & Bigote", "Líneas simétricas y brillo natural"),
        ("galeria_3", "Corte Pompadour Texturizado", "Volumen y acabado con pomada mate"),
        ("galeria_4", "Ritual Toalla Caliente", "Momento de relajación y cuidado de la piel"),
        ("galeria_5", "Taper Fade Clásico", "Elegancia atemporal para el día a día"),
        ("galeria_6", "Diseño de Barba y Cuello", "Definición milimétrica con navaja"),
    ]
    for slug, tit, sub in galeria:
        generar_placeholder("galeria", slug, tit, sub, 800, 800)
        
    # Blog
    blog = [
        ("guia_cuidado_barba", "Guía Definitiva para el Cuidado de tu Barba", "Aprende a hidratar, peinar y mantener el brillo ideal"),
        ("fade_segun_tu_rostro", "¿Qué Tipo de Fade Favorece la Forma de tu Rostro?", "Consejos de visagismo por nuestros Master Barbers"),
        ("ritual_afeitado_clasico", "El Secreto del Afeitado Tradicional con Toalla Caliente", "Por qué este clásico nunca pasará de moda"),
    ]
    for slug, tit, sub in blog:
        generar_placeholder("blog", slug, tit, sub, 900, 600)

if __name__ == "__main__":
    crear_carpetas()
    generar_favicons()
    generar_og_image()
    generar_catalogo_demo()
    print("Todos los assets iniciales han sido generados exitosamente.")
