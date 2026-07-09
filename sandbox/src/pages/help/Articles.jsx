import { Link, useParams } from 'react-router-dom'

export const ARTICLES = {
  'getting-started': {
    title: 'Getting Started',
    body: 'Begin at the home page and pick a section. Each section branches further.',
    related: ['navigation-basics', 'account-setup'],
  },
  'navigation-basics': {
    title: 'Navigation Basics',
    body: 'Use breadcrumbs to understand where you are. Tabs and pills switch sub-views.',
    related: ['getting-started'],
  },
  'account-setup': {
    title: 'Account Setup',
    body: 'Sign in first, then visit Settings → Profile to configure your account.',
    related: ['getting-started', 'navigation-basics'],
  },
}

export function ArticleList() {
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Articles</h3>
      <ul>
        {Object.entries(ARTICLES).map(([slug, a]) => (
          <li key={slug} style={{ marginBottom: 8 }}>
            <Link to={`/help/articles/${slug}`}>{a.title}</Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ArticleDetail() {
  const { slug } = useParams()
  const article = ARTICLES[slug]

  if (!article) {
    return (
      <div className="card">
        <p>Article not found.</p>
        <Link to="/help/articles">← All articles</Link>
      </div>
    )
  }

  return (
    <div className="card">
      <Link to="/help/articles">← All articles</Link>
      <h3>{article.title}</h3>
      <p className="muted">{article.body}</p>
      <h4>Related</h4>
      <div className="row">
        {article.related.map((r) => (
          <Link className="badge" key={r} to={`/help/articles/${r}`}>{ARTICLES[r]?.title || r}</Link>
        ))}
      </div>
    </div>
  )
}
