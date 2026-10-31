// Versão B: mesma entrada da versão A (saida/cortado.mp4 + saida/cortado.json), visual em React.
// Render: ver scripts/render_remotion.sh
import React from 'react';
import {registerRoot, Composition, AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame,
  useVideoConfig, spring, interpolate, Sequence} from 'remotion';
import estilo from '../../estilo.json';
import {blocos} from './blocos.js';

const F = `'${estilo.fonte}', sans-serif`;
const segura = {left: 70, right: 70};

const Legenda = ({palavras, destaques}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const lista = React.useMemo(() => blocos(palavras, estilo.legenda.palavras_por_bloco), [palavras]);
  const b = lista.find((x) => t >= x.i && t < x.f);
  if (!b) return null;
  const entrada = spring({frame: frame - Math.round(b.i * fps), fps, config: {damping: 14, stiffness: 220}});
  return (
    <div style={{position: 'absolute', ...segura, bottom: 1920 - estilo.legenda.y_base, textAlign: 'center',
      transform: `translateY(${(1 - entrada) * 14}px)`}}>
      {b.palavras.map((w, k) => {
        const ativa = t >= w.i && (k + 1 < b.palavras.length ? t < b.palavras[k + 1].i : true);
        const chave = destaques.includes(w.p.replace(/[.,!?…]/g, '').toLowerCase());
        const pop = ativa ? spring({frame: frame - Math.round(w.i * fps), fps, config: {damping: 10, stiffness: 300}}) : 0;
        return (
          <span key={k} style={{display: 'inline-block', margin: '0 15px', fontFamily: F, fontWeight: 800,
            fontSize: estilo.legenda.tamanho, lineHeight: 1.15, color: chave ? estilo.cor_destaque : 'white',
            WebkitTextStroke: '12px black', paintOrder: 'stroke fill',
            textShadow: '0 6px 18px rgba(0,0,0,.35)', transform: `scale(${1 + 0.12 * pop})`}}>{w.p}</span>
        );
      })}
    </div>
  );
};

const Cartao = ({texto, tamanho, topo}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 13, stiffness: 200}});
  const linhas = texto.split(' · ');
  return (
    <div style={{position: 'absolute', ...segura, top: topo, display: 'flex', justifyContent: 'center'}}>
      <div style={{background: 'white', color: '#111', borderRadius: 22, padding: '16px 30px', textAlign: 'center',
        fontFamily: F, fontWeight: 800, fontSize: tamanho, lineHeight: 1.12, boxShadow: '0 10px 30px rgba(0,0,0,.25)',
        transform: `scale(${0.6 + 0.4 * s}) rotate(${(1 - s) * -4}deg)`, opacity: s}}>
        {linhas.map((l, k) => <div key={k} style={k ? {fontSize: tamanho * 0.8, fontWeight: 700} : {}}>{l}</div>)}
      </div>
    </div>
  );
};

const Selo = ({texto, cor, alinhar, topo, tamanho}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 15}});
  const pulso = 1 + 0.035 * Math.max(0, Math.sin((frame / fps) * Math.PI * 0.8)) ** 8;
  return (
    <div style={{position: 'absolute', top: topo, [alinhar]: 70, background: cor, color: 'white',
      borderRadius: 40, padding: '10px 22px', fontFamily: F, fontWeight: 700, fontSize: tamanho,
      transform: `translateX(${(1 - s) * (alinhar === 'right' ? 140 : -140)}px) scale(${pulso})`, opacity: s}}>{texto}</div>
  );
};

const Reel = ({dados, video}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  // Punch-in com rampa curta (4 quadros) em vez do zoom seco da versão A.
  let zoom = 1;
  for (const z of dados.zooms) {
    const alvo = z.escala || estilo.zoom_padrao;
    const a = Math.round(z.de * fps), b = Math.round(z.ate * fps);
    zoom = Math.max(zoom, interpolate(frame, [a, a + 4, b - 4, b], [1, alvo, alvo, 1],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  }
  const finais = dados.textos.filter((x) => x.tipo === 'final').map((x) => x.de);
  const seq = (x, el) => {
    const de = Math.round(x.de * fps);
    let ate = Math.round(x.ate * fps);
    if (x.tipo === 'cta' && finais.length) ate = Math.round(finais[0] * fps);
    return <Sequence key={x.tipo + x.de} from={de} durationInFrames={Math.max(1, ate - de)} layout="none">{el}</Sequence>;
  };
  return (
    <AbsoluteFill style={{background: 'black'}}>
      <AbsoluteFill style={{transform: `scale(${zoom})`}}><OffthreadVideo src={staticFile(video)} /></AbsoluteFill>
      {dados.textos.map((x) => {
        if (x.tipo === 'gancho' || x.tipo === 'final') return seq(x, <Cartao texto={x.texto} tamanho={estilo.gancho.tamanho} topo={estilo.gancho.y_topo} />);
        if (x.tipo === 'meio') return seq(x, <Cartao texto={x.texto} tamanho={60} topo={estilo.gancho.y_topo} />);
        if (x.tipo === 'cta') return seq(x, <Selo texto={x.texto} cor={estilo.cor_cta} alinhar="right" topo={estilo.cta.y_topo} tamanho={estilo.cta.tamanho} />);
        if (x.tipo === 'rotulo') return seq(x, <Selo texto={x.texto} cor="rgba(0,0,0,.55)" alinhar="left" topo={estilo.rotulo.y_topo} tamanho={estilo.rotulo.tamanho} />);
        return null;
      })}
      <Legenda palavras={dados.palavras} destaques={dados.destaques.map((d) => d.toLowerCase())} />
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="Reel" component={Reel} width={1080} height={1920} fps={30} durationInFrames={30}
    defaultProps={{dados: {duracao_s: 1, palavras: [], textos: [], zooms: [], destaques: []}, video: 'cortado.mp4'}}
    calculateMetadata={({props}) => ({durationInFrames: Math.round(props.dados.duracao_s * 30)})} />
));
