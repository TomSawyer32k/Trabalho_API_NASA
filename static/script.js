const API_URL = "/api";
const cache = new Map();

const $ = (id) => document.getElementById(id);

function textoCurto(texto, limite = 150) {
  if (!texto) return "Sem descrição disponível.";
  return texto.length > limite ? `${texto.substring(0, limite)}...` : texto;
}

function mostrarErro(id, mensagem = "Não foi possível carregar os dados agora. Tente novamente em alguns segundos.") {
  $(id).innerHTML = `<p class="status erro">${mensagem}</p>`;
}

function mostrarCarregando(id, quantidade = 3) {
  $(id).innerHTML = `
    <div class="grid">
      ${Array.from({ length: quantidade }).map(() => `
        <div class="skeleton-card">
          <div class="skeleton-img"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line small"></div>
        </div>
      `).join("")}
    </div>
  `;
}

async function api(endpoint) {
  const url = `${API_URL}${endpoint}`;

  if (cache.has(url)) {
    return cache.get(url);
  }

  const resposta = await fetch(url);

  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => null);
    throw new Error(erro?.detail || "Erro ao consultar a API.");
  }

  const dados = await resposta.json();
  cache.set(url, dados);
  return dados;
}

function cardImagem(imagem, titulo, descricao) {
  return `
    <article class="item">
      <img
        src="${imagem}"
        alt="${titulo}"
        loading="lazy"
        decoding="async"
        onerror="this.closest('.item').remove()"
      >
      <h3>${titulo}</h3>
      <p>${textoCurto(descricao, 140)}</p>
    </article>
  `;
}

function formatarData(data) {
  return data.toISOString().split("T")[0];
}

function periodoAsteroides() {
  const hoje = new Date();
  const fim = new Date(hoje);
  const periodo = $("periodo-asteroide").value;

  if (periodo === "3dias") fim.setDate(fim.getDate() + 2);
  if (periodo === "7dias") fim.setDate(fim.getDate() + 6);

  return {
    inicio: formatarData(hoje),
    fim: formatarData(fim)
  };
}

function urlImagemEpic(item) {
  const data = item.date.split(" ")[0];
  const [ano, mes, dia] = data.split("-");
  return `https://epic.gsfc.nasa.gov/archive/natural/${ano}/${mes}/${dia}/png/${item.image}.png`;
}

async function carregarCategoriasMarte() {
  try {
    const dados = await api("/mars/categories");
    const categorias = dados.categorias || [];

    $("categoria-marte").innerHTML = categorias.map(categoria => `
      <option value="${categoria.valor}">
        ${categoria.nome}
      </option>
    `).join("");
  } catch {
    $("categoria-marte").innerHTML = `<option value="">Erro ao carregar categorias</option>`;
  }
}

async function buscarApod() {
  mostrarCarregando("apod", 1);

  try {
    const dados = await api("/apod");

    if (!dados.url || dados.media_type === "text") {
      $("apod").innerHTML = `
        <div class="result-feature">
          <div>
            <h3>${dados.title}</h3>
            <p><strong>Data:</strong> ${dados.date}</p>
            <p>${dados.explanation}</p>
          </div>
        </div>
      `;
      return;
    }

    $("apod").innerHTML = `
      <div class="result-feature">
        <div>
          <h3>${dados.title || "Imagem astronômica"}</h3>
          <p><strong>Data:</strong> ${dados.date || "Não informado"}</p>
          <p>${dados.explanation || "Sem explicação disponível."}</p>
        </div>
        <div>
          ${
            dados.media_type === "image"
              ? `<img src="${dados.url}" alt="${dados.title}" loading="lazy" decoding="async">`
              : `<iframe loading="lazy" width="100%" height="400" src="${dados.url}"></iframe>`
          }
        </div>
      </div>
    `;
  } catch (erro) {
    mostrarErro("apod", erro.message);
  }
}

async function buscarMarte() {
  const categoria = $("categoria-marte").value;
  const limite = $("limite-marte").value;

  if (!categoria) {
    mostrarErro("marte", "Escolha uma categoria para pesquisar.");
    return;
  }

  mostrarCarregando("marte");

  try {
    const dados = await api(`/mars/images?categoria=${encodeURIComponent(categoria)}&limite=${limite}`);
    const imagens = dados.imagens || [];

    if (!imagens.length) {
      mostrarErro("marte", "Nenhuma imagem foi encontrada para essa categoria.");
      return;
    }

    $("marte").innerHTML = `
      <p class="status">Fonte: <strong>${dados.fonte}</strong></p>
      <div class="grid">
        ${imagens.map(img => cardImagem(img.imagem, img.titulo, img.descricao)).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("marte", erro.message);
  }
}

async function buscarAsteroides() {
  const periodo = periodoAsteroides();

  mostrarCarregando("asteroides");

  try {
    const dados = await api(`/asteroids?start_date=${periodo.inicio}&end_date=${periodo.fim}`);
    const lista = dados.asteroides || [];

    if (!lista.length) {
      mostrarErro("asteroides", "Nenhum asteroide foi encontrado nesse período.");
      return;
    }

    $("asteroides").innerHTML = `
      <div class="grid">
        ${lista.map(ast => `
          <article class="item">
            <span class="tag">${ast.dangerous ? "Atenção" : "Monitorado"}</span>
            <h3>${ast.name}</h3>
            <p><strong>Data:</strong> ${ast.date}</p>
            <p><strong>Potencialmente perigoso:</strong> ${ast.dangerous ? "Sim" : "Não"}</p>
            <p><strong>Magnitude:</strong> ${ast.magnitude}</p>
            <p><strong>Diâmetro estimado:</strong> ${ast.diameter?.toFixed(2)} metros</p>
          </article>
        `).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("asteroides", erro.message);
  }
}

async function buscarCatalogoAsteroides() {
  mostrarCarregando("catalogo-asteroides");

  try {
    const dados = await api("/asteroids/catalog");

    if (!dados.length) {
      mostrarErro("catalogo-asteroides", "Nenhum asteroide foi encontrado.");
      return;
    }

    $("catalogo-asteroides").innerHTML = `
      <div class="grid">
        ${dados.map(ast => `
          <article class="item">
            <span class="tag">${ast.perigoso ? "Atenção" : "Monitorado"}</span>
            <h3>${ast.nome}</h3>
            <p><strong>ID:</strong> ${ast.id}</p>
            <p><strong>Magnitude:</strong> ${ast.magnitude}</p>
          </article>
        `).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("catalogo-asteroides", erro.message);
  }
}

async function buscarEpic() {
  const limite = $("limite-epic").value;

  mostrarCarregando("epic");

  try {
    const dados = await api(`/epic?limite=${limite}`);

    if (!dados.length) {
      mostrarErro("epic", "Nenhuma imagem da Terra foi encontrada agora.");
      return;
    }

    $("epic").innerHTML = `
      <div class="grid">
        ${dados.map(item => cardImagem(
          urlImagemEpic(item),
          "Imagem da Terra",
          `Registro feito em ${item.date}.`
        )).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("epic", erro.message);
  }
}

async function buscarImagens() {
  const categoria = $("categoria-imagens").value;
  const limite = $("limite-imagens").value;

  mostrarCarregando("imagens");

  try {
    const dados = await api(`/images/search?categoria=${categoria}&limite=${limite}`);
    const imagens = dados.imagens || [];

    if (!imagens.length) {
      mostrarErro("imagens", "Nenhuma imagem foi encontrada para essa categoria.");
      return;
    }

    $("imagens").innerHTML = `
      <div class="grid">
        ${imagens.map(img => cardImagem(img.imagem, img.titulo, img.descricao)).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("imagens", erro.message);
  }
}

async function buscarClimaEspacial() {
  mostrarCarregando("clima-espacial");

  try {
    const dados = await api("/space-weather");

    if (!dados.length) {
      mostrarErro("clima-espacial", "Nenhum evento solar foi encontrado no momento.");
      return;
    }

    $("clima-espacial").innerHTML = `
      <div class="grid">
        ${dados.map(evento => `
          <article class="item">
            <span class="tag">Atividade solar</span>
            <h3>${evento.flrID || "Evento solar"}</h3>
            <p><strong>Classe:</strong> ${evento.classType || "Não informado"}</p>
            <p><strong>Início:</strong> ${evento.beginTime || "Não informado"}</p>
            <p><strong>Pico:</strong> ${evento.peakTime || "Não informado"}</p>
            <p><strong>Região:</strong> ${evento.sourceLocation || "Não informado"}</p>
          </article>
        `).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("clima-espacial", erro.message);
  }
}

async function buscarEventos() {
  const limite = $("limite-eventos").value;

  mostrarCarregando("eventos");

  try {
    const dados = await api(`/eonet/events?limite=${limite}`);
    const eventos = dados.events || [];

    if (!eventos.length) {
      mostrarErro("eventos", "Nenhum evento natural foi encontrado agora.");
      return;
    }

    $("eventos").innerHTML = `
      <div class="grid">
        ${eventos.map(evento => `
          <article class="item">
            <span class="tag">${evento.categories?.[0]?.title || "Evento natural"}</span>
            <h3>${evento.title}</h3>
            <p><strong>Fonte:</strong> NASA EONET</p>
            <p><strong>ID:</strong> ${evento.id}</p>
          </article>
        `).join("")}
      </div>
    `;
  } catch (erro) {
    mostrarErro("eventos", erro.message);
  }
}

window.addEventListener("load", async () => {
  await carregarCategoriasMarte();
  buscarApod();
});