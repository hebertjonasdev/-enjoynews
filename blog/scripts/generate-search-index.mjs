import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

const postsDir = path.resolve('src/content/posts');
const outputPath = path.resolve('public/search-index.json');

if (!fs.existsSync(postsDir)) {
  console.log('Posts directory not found, creating empty index');
  fs.writeFileSync(outputPath, JSON.stringify([]));
  process.exit(0);
}

const files = fs.readdirSync(postsDir).filter(f => f.endsWith('.mdx'));

const index = files.map(file => {
  const content = fs.readFileSync(path.join(postsDir, file), 'utf-8');
  const { data } = matter(content);

  return {
    title: data.title,
    description: data.description,
    slug: `/post/${file.replace('.mdx', '')}`,
    category: data.category,
    tags: data.tags || [],
    pubDate: data.pubDate,
    heroImage: data.heroImage,
    importance: data.importance,
    kicker: data.kicker,
    sourceName: data.sourceName,
  };
});

index.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime());

fs.writeFileSync(outputPath, JSON.stringify(index, null, 2));
console.log(`Generated search index with ${index.length} articles`);