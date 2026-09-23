export default function HomePage() {
  return (
    <div className="px-4 pt-8">
      <header className="text-center mb-10">
        <h1 className="text-3xl font-light tracking-[0.3em] text-charcoal">VELORA</h1>
        <p className="mt-2 text-sm text-warm-gold tracking-widest uppercase">Premium Fashion</p>
      </header>

      <section className="mb-8">
        <div className="bg-champagne/60 rounded-sm p-8 text-center">
          <p className="text-lg font-light">Новая коллекция</p>
          <p className="text-sm mt-2 opacity-70">Скоро в продаже</p>
        </div>
      </section>

      <section>
        <h2 className="text-sm tracking-widest uppercase mb-4 text-charcoal/70">Популярное</h2>
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-cream rounded-sm aspect-[3/4] flex items-center justify-center">
              <span className="text-xs text-charcoal/40">Товар {i}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
