import rss from '@astrojs/rss';

export async function GET(context) {
  const posts = await Astro.glob('../content/posts/*.mdx');
  const sortedPosts = posts
    .map(post => ({
      ...post,
      data: post.frontmatter,
      link: `/post/${post.file.split('/').pop()?.replace('.mdx', '')}`,
    }))
    .sort((a, b) => new Date(b.data.pubDate).getTime() - new Date(a.data.pubDate).getTime())
    .slice(0, 50);

  return rss({
    title: 'EnjoyNews',
    description: 'Jornalismo automatizado com curadoria editorial. Notícias do Brasil, mundo e Latino-América.',
    site: context.site,
    items: sortedPosts.map(post => ({
      title: post.data.title,
      description: post.data.description,
      link: post.link,
      pubDate: new Date(post.data.pubDate),
      categories: post.data.tags || [],
      customData: `<source>${post.data.sourceName}</source><category>${post.data.category}</category>`,
    })),
    customData: `<language>pt-BR</language><managingEditor>bot@enjoynews.com.br</managingEditor><webMaster>bot@enjoynews.com.br</webMaster>`,
  });
}