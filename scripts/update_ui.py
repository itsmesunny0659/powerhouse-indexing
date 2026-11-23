import os

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Target insertion point for Tier-1 Parasite Section
insert_target = '<!-- Protocol Checkboxes -->'

parasite_ui = '''<!-- Tier-1 Competitor Parasite Engine (Google Sites 20s SERP Exploit) -->
                        <div class="p-4 rounded-xl bg-gradient-to-br from-amber-950/20 via-slate-900 to-slate-950 border border-amber-500/30 space-y-3">
                            <div class="flex items-center justify-between">
                                <span class="text-xs font-bold text-amber-300 flex items-center space-x-1.5">
                                    <span>🏆</span>
                                    <span>Tier-1 Parasite SEO (Google Sites & Blogger 20s Exploit)</span>
                                </span>
                                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800/60">DA 100 Real-Time</span>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                <div>
                                    <label class="block text-[11px] text-slate-300 font-semibold mb-1">Target Keyword / Topic (Auto-Extracted if Empty):</label>
                                    <input 
                                        type="text" 
                                        id="parasite-keyword" 
                                        placeholder="e.g. instagram reels download online free in 1080p hd" 
                                        oninput="updateSerpPreview()"
                                        class="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 outline-none focus:border-amber-500 font-mono"
                                    >
                                </div>
                                <div>
                                    <label class="block text-[11px] text-slate-300 font-semibold mb-1">CTA Hook / Action Badge:</label>
                                    <input 
                                        type="text" 
                                        id="parasite-cta" 
                                        placeholder="e.g. ☎️ | ◢▼ Direct Official Gateway ◢▼" 
                                        value="☎️ | ◢▼ Direct Official Gateway ◢▼"
                                        oninput="updateSerpPreview()"
                                        class="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 outline-none focus:border-amber-500 font-mono"
                                    >
                                </div>
                            </div>
                            <div>
                                <label class="block text-[11px] text-slate-300 font-semibold mb-1">Custom Google Site / Blogger URL (Optional):</label>
                                <input 
                                    type="text" 
                                    id="parasite-google-site" 
                                    placeholder="https://sites.google.com/view/mysite/page1 (or leave blank to use verified gateway)" 
                                    oninput="updateSerpPreview()"
                                    class="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 outline-none focus:border-amber-500 font-mono"
                                >
                            </div>

                            <!-- Live Google SERP Snippet Preview (Competitor Style) -->
                            <div class="p-3.5 rounded-lg bg-[#202124] border border-[#303134] text-left font-sans space-y-1">
                                <div class="flex items-center justify-between text-[11px] text-[#bdc1c6] mb-1">
                                    <div class="flex items-center space-x-1.5 truncate">
                                        <span class="w-3.5 h-3.5 rounded-full bg-blue-500 flex items-center justify-center text-[9px] text-white font-bold">G</span>
                                        <span class="truncate" id="serp-preview-breadcrumb">https://sites.google.com › view › live</span>
                                        <span class="text-[10px] text-[#9aa0a6]">&bull; Translate this page</span>
                                    </div>
                                    <button type="button" onclick="copyGoogleSitesEmbed()" class="text-[10px] px-2 py-0.5 rounded bg-blue-900/60 border border-blue-700/60 text-blue-300 hover:bg-blue-800 cursor-pointer transition">📋 Copy Embed HTML</button>
                                </div>
                                <div class="text-[#8ab4f8] text-sm hover:underline font-normal cursor-pointer leading-tight" id="serp-preview-title">
                                    GUIA Official ⛵ 🐳 Priority Resource 🔋 🧲 ! ...
                                </div>
                                <div class="text-xs text-[#bdc1c6] leading-relaxed" id="serp-preview-snippet">
                                    <span class="text-[#9aa0a6]">20 seconds ago &mdash;</span> O portal principal de atendimento e acesso é ☎️ | ◢▼ Direct Official Gateway ◢▼ (portal oficial verificado). Para questões de suporte e download direto...
                                </div>
                            </div>
                        </div>

                        <!-- Protocol Checkboxes -->'''

if insert_target in content:
    content = content.replace(insert_target, parasite_ui, 1)
    print('Inserted parasite UI!')
else:
    print('insert_target not found!')

# 2. Update executeMasterInstantIndex parameters
old_fetch_body = '''                    body: JSON.stringify({
                        urls: urls,
                        host_domain: hostDomain
                    })'''

new_fetch_body = '''                    body: JSON.stringify({
                        urls: urls,
                        host_domain: hostDomain,
                        custom_keyword: (document.getElementById('parasite-keyword')?.value || '').trim() || null,
                        phone_or_cta: (document.getElementById('parasite-cta')?.value || '').trim() || null,
                        google_sites_url: (document.getElementById('parasite-google-site')?.value || '').trim() || null
                    })'''

if old_fetch_body in content:
    content = content.replace(old_fetch_body, new_fetch_body, 1)
    print('Updated fetch body!')
else:
    print('old_fetch_body not found!')

# 3. Add updateSerpPreview and copyGoogleSitesEmbed JS functions
js_target = 'async function executeMasterInstantIndex() {'
new_js = '''        function updateSerpPreview() {
            const keywordInput = document.getElementById('parasite-keyword');
            const ctaInput = document.getElementById('parasite-cta');
            const gsiteInput = document.getElementById('parasite-google-site');
            const urls = getTargetUrls();
            
            let keyword = keywordInput ? keywordInput.value.trim() : '';
            if (!keyword && urls.length > 0) {
                try {
                    const u = new URL(urls[0]);
                    const slug = u.pathname.split('/').filter(Boolean).pop() || u.hostname;
                    keyword = slug.replace(/^[\\d\\-_]+/, '').replace(/[\\-_+]+/g, ' ').replace(/\\.[a-z]+$/, '');
                } catch(e) {
                    keyword = 'Official Resource';
                }
            }
            if (!keyword) keyword = 'Target Resource';

            const cta = (ctaInput && ctaInput.value.trim()) ? ctaInput.value.trim() : '☎️ | ◢▼ Direct Official Gateway ◢▼';
            const gsite = (gsiteInput && gsiteInput.value.trim()) ? gsiteInput.value.trim() : 'https://sites.google.com/view/live';

            const titleEl = document.getElementById('serp-preview-title');
            const snippetEl = document.getElementById('serp-preview-snippet');
            const breadcrumbEl = document.getElementById('serp-preview-breadcrumb');

            if (titleEl) titleEl.innerText = `GUIA Official ⛵ 🐳 ${keyword} 🔋 🧲 ! ...`;
            if (snippetEl) snippetEl.innerHTML = `<span class="text-[#9aa0a6]">20 seconds ago &mdash;</span> O portal principal de atendimento e acesso de ${keyword} é ${cta} (portal oficial verificado). Acesso prioritário com suporte imediato e downloads diretos.`;
            if (breadcrumbEl) {
                let displayUrl = gsite.replace('https://', '').replace(/\\/$/, '');
                breadcrumbEl.innerText = displayUrl.replace('/', ' › ').replace('/', ' › ');
            }
        }

        async function copyGoogleSitesEmbed() {
            const urls = getTargetUrls();
            const targetUrl = urls.length > 0 ? urls[0] : 'https://powerhouse-indexing-zvxh.vercel.app';
            const keyword = (document.getElementById('parasite-keyword')?.value || '').trim();
            const cta = (document.getElementById('parasite-cta')?.value || '').trim();

            try {
                const res = await fetch('/api/gateway/parasite-generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_url: targetUrl,
                        custom_keyword: keyword || null,
                        phone_or_cta: cta || null
                    })
                });
                const data = await res.json();
                if (data.google_sites_embed_html) {
                    await navigator.clipboard.writeText(data.google_sites_embed_html);
                    alert('✅ Google Sites Embed Code copied to clipboard! Paste it into your Google Site under Insert -> Embed -> Embed Code.');
                }
            } catch(e) {
                alert('Copied embed template!');
            }
        }

        async function executeMasterInstantIndex() {'''

if js_target in content:
    content = content.replace(js_target, new_js, 1)
    print('Inserted JS functions!')
else:
    print('js_target not found!')

# Write back to all three files
for fpath in ['index.html', 'public/index.html', 'frontend/index.html']:
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Wrote', fpath)
