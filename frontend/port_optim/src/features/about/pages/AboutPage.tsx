import React from 'react';
import { AboutSection } from '../components/AboutSection';
import about1 from '../../../assets/about_1.jpg';
import about2 from '../../../assets/about_2.jpg';
import about3 from '../../../assets/about_3.jpg';
import './AboutPage.css';

export const AboutPage: React.FC = () => {
  return (
    <div className="about-page">
      {/* Page Header */}
      <div className="about-page__header">
        <h1 className="about-page__title">About This Dashboard</h1>
        <p className="about-page__subtitle">
          Turn investment ideas into structured portfolios, test them, and stress-test assumptions — all in one place.
        </p>
      </div>

      {/* Sections */}
      <div className="about-page__sections">

        {/* Section 1: Black-Litterman */}
        <AboutSection title="Black-Litterman Portfolio Construction" image={about1}>
          <div className="about-content">
            <div className="about-content__block">
              <h3 className="about-content__heading">What this does</h3>
              <p>The Black-Litterman engine combines:</p>
              <ul className="about-content__list">
                <li>Market equilibrium (what the market already implies)</li>
                <li>Your views (asset-level or factor-level)</li>
                <li>Confidence levels</li>
              </ul>
              <p className="about-content__output">
                <strong>Output:</strong> optimized portfolio allocations with clear risk/return trade-offs
              </p>
            </div>

            <div className="about-content__block">
              <h3 className="about-content__heading">The Problem (Traditional Approach)</h3>
              <p>In a typical setup, you would need to:</p>
              <ul className="about-content__list">
                <li>Manually construct P, Q, and &Omega; matrices</li>
                <li>Ensure dimensional consistency</li>
                <li>Encode views numerically (often unintuitive)</li>
                <li>Debug fragile matrix setups</li>
              </ul>
              <p>This is:</p>
              <ul className="about-content__list">
                <li>Error-prone</li>
                <li>Time-consuming</li>
                <li>Not flexible for iterative research</li>
              </ul>
            </div>

            <div className="about-content__block">
              <h3 className="about-content__heading">The Advantage Here</h3>
              <p>This dashboard removes that friction entirely:</p>

              <div className="about-content__feature-list">
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Natural Language Views</span>
                  <p className="about-content__feature-description">
                    "Tech will outperform by 5%"<br />
                    "Apple will beat Microsoft by 2%"
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Automatic Translation</span>
                  <p className="about-content__feature-description">
                    Converts text to structured BL inputs internally
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Seamless Blending</span>
                  <p className="about-content__feature-description">
                    Combines your views with market priors
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Full Transparency</span>
                  <p className="about-content__feature-description">
                    Prior vs Posterior allocations &mdash; Efficient frontier &mdash; Contribution analysis
                  </p>
                </div>
              </div>

              <p className="about-content__closing">
                You get the power of Black-Litterman without dealing with matrices directly, while retaining control and interpretability.
              </p>
            </div>
          </div>
        </AboutSection>

        {/* Section 2: Portfolio Backtesting */}
        <AboutSection title="Portfolio Backtesting" image={about2}>
          <div className="about-content">
            <div className="about-content__block">
              <h3 className="about-content__heading">What this does</h3>
              <p>Allows you to:</p>
              <ul className="about-content__list">
                <li>Take a strategy or thesis</li>
                <li>Convert it into a structured portfolio</li>
                <li>Test it on historical data</li>
              </ul>
              <p className="about-content__output">
                <strong>Output:</strong> performance metrics and equity curves
              </p>
            </div>

            <div className="about-content__block">
              <h3 className="about-content__heading">The Problem (Traditional Approach)</h3>
              <p>Backtesting usually requires:</p>
              <ul className="about-content__list">
                <li>Writing strategy code</li>
                <li>Manually defining signals and weights</li>
                <li>Maintaining separate pipelines</li>
              </ul>
              <p>This creates a disconnect between:</p>
              <ul className="about-content__list">
                <li>Research ideas</li>
                <li>Actual tested strategies</li>
              </ul>
            </div>

            <div className="about-content__block">
              <h3 className="about-content__heading">The Advantage Here</h3>

              <div className="about-content__feature-list">
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Direct View → Strategy Pipeline</span>
                  <p className="about-content__feature-description">
                    The same views used in Black-Litterman can drive backtests
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Rapid Iteration</span>
                  <p className="about-content__feature-description">
                    Modify views and instantly test new strategies
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Integrated Evaluation</span>
                  <p className="about-content__feature-description">
                    CAGR, Sharpe, drawdown &mdash; Equity curve visualization
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Consistent Recipe System</span>
                  <p className="about-content__feature-description">
                    Your thesis is stored once and reused
                  </p>
                </div>
              </div>

              <p className="about-content__closing">
                This creates a tight feedback loop between idea and validation.
              </p>
            </div>
          </div>
        </AboutSection>

        {/* Section 3: Agent-Based Stress Testing */}
        <AboutSection title="Agent-Based Stress Testing &amp; Analysis" image={about3}>
          <div className="about-content">
            <div className="about-content__block">
              <h3 className="about-content__heading">What this does</h3>
              <p>
                The agent acts as a research assistant on top of the Black-Litterman engine.
              </p>
              <p>You can give it goals like:</p>
              <ul className="about-content__list">
                <li>Make this portfolio more conservative</li>
                <li>Reduce exposure to growth risk</li>
                <li>Test sensitivity to confidence levels</li>
              </ul>
            </div>

            <div className="about-content__block">
              <h3 className="about-content__heading">How it Works</h3>
              <ul className="about-content__list">
                <li>Loads your current portfolio recipe</li>
                <li>Runs baseline Black-Litterman allocation</li>
                <li>Explores alternative scenarios using tools</li>
              </ul>
            </div>

            <div className="about-content__block">
              <h3 className="about-content__heading">The Advantage Here</h3>

              <div className="about-content__feature-list">
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Stress Testing Assumptions</span>
                  <p className="about-content__feature-description">
                    Analyze sensitivity to views and parameters
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">View Fragility Analysis</span>
                  <p className="about-content__feature-description">
                    Identify which views drive instability
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Scenario Exploration</span>
                  <p className="about-content__feature-description">
                    Test multiple alternatives automatically
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Insight Generation</span>
                  <p className="about-content__feature-description">
                    Produces a final recommendation with reasoning
                  </p>
                </div>
                <div className="about-content__feature">
                  <span className="about-content__feature-label">Full Audit Trail</span>
                  <p className="about-content__feature-description">
                    Logs every step and decision
                  </p>
                </div>
              </div>

              <p className="about-content__closing">
                Instead of a single optimization output, you get a full research process with reasoning and evidence.
              </p>
            </div>
          </div>
        </AboutSection>

      </div>
    </div>
  );
};
