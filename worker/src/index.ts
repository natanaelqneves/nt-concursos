interface Env {
  GITHUB_TOKEN: string;
  GITHUB_REPO: string;
  WORKFLOW_FILE: string;
  REF: string;
}

async function disparar(env: Env): Promise<void> {
  const url = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}/dispatches`;
  for (let tentativa = 1; tentativa <= 3; tentativa++) {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ntconcursos-disparo",
      },
      body: JSON.stringify({ ref: env.REF }),
    });
    if (resp.status === 204) return;
    // 4xx (token/permissão) não melhora com nova tentativa.
    if (resp.status < 500) throw new Error(`dispatch recusado: ${resp.status} ${await resp.text()}`);
    await new Promise((r) => setTimeout(r, 5000 * tentativa));
  }
  throw new Error("dispatch falhou após 3 tentativas; o cron reserva das 04h30 cobre este dia");
}

export default {
  async scheduled(_evento: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(disparar(env));
  },
};
