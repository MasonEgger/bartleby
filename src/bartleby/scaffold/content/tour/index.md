---
title: Feature Tour
description: Every Markdown feature Bartleby renders, each shown as its source followed by the result.
---

Each section below shows the Markdown you write in a code block, then the result it produces right after it.
Copy a source block into any page under `content/` to use it.
When you no longer need this page, delete `content/tour/` and its entry in the `nav` section of `bartleby.yml`.

## Code Blocks

### Labels

Add a label above a code block with `[label TEXT]` as the first line inside the fence.

````
```python
[label app.py]
from flask import Flask

app = Flask(__name__)
```
````

```python
[label app.py]
from flask import Flask

app = Flask(__name__)
```

### Secondary Labels

Add a second label inside the block with `[secondary_label TEXT]`.
It works well for showing output.

````
```
[secondary_label Output]
Hello, world!
```
````

```
[secondary_label Output]
Hello, world!
```

### Environments

Tint a block with `[environment NAME]` to tell server environments apart.
The names are `local`, `second`, `third`, `fourth`, and `fifth`.

````
```
[environment local]
ssh user@local-server
```
````

```
[environment local]
ssh user@local-server
```

````
```
[environment third]
ssh user@production-server
```
````

```
[environment third]
ssh user@production-server
```

### Line Numbers and Prompts

Flags in the info string prefix every line.
`line_numbers` numbers the lines, `command` adds a `$` prompt, `super_user` adds a `#` prompt, and `custom_prefix(TEXT)` adds your own.

````
```line_numbers,python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"
```
````

```line_numbers,python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"
```

````
```command
sudo apt update
sudo apt install nginx
```
````

```command
sudo apt update
sudo apt install nginx
```

````
```custom_prefix(mysql>)
SELECT * FROM users;
```
````

```custom_prefix(mysql>)
SELECT * FROM users;
```

### Directives Combined

Flags and directives stack.

````
```command
[environment local]
[label server.sh]
ssh root@192.168.1.1
apt update && apt upgrade -y
```
````

```command
[environment local]
[label server.sh]
ssh root@192.168.1.1
apt update && apt upgrade -y
```

### Highlight Markers

Wrap text in `<^>` markers to highlight it.
The markers work in prose, in inline code, and inside code blocks.
A backslash in front of a marker prints it literally, which is how the sources here show the syntax.

````
This sentence has a \<^>highlighted phrase\<^> in it.

Check the `config.\<^>timeout\<^>` value.

```python
def greet(name):
    print(f"Hello, \<^>{name}\<^>!")
```
````

This sentence has a <^>highlighted phrase<^> in it.

Check the `config.<^>timeout<^>` value.

```python
def greet(name):
    print(f"Hello, <^>{name}<^>!")
```

### Inline Code Highlighting

A language name and a colon turn inline code into highlighted code.

````
The `#!python print("hello")` call writes a line.
````

The `#!python print("hello")` call writes a line.

## Text Formatting

### Marked Text

Two equals signs mark text.

````
This is ==marked text==.
````

This is ==marked text==.

### Inserted Text and Superscript

Two carets insert text.
One caret sets a superscript.

````
This is ^^inserted text^^ and x^2^.
````

This is ^^inserted text^^ and x^2^.

### Deleted Text and Subscript

Two tildes delete text.
One tilde sets a subscript.

````
This is ~~deleted text~~ and H~2~O.
````

This is ~~deleted text~~ and H~2~O.

### Keyboard Keys

Two plus signs around a key combination draw the keys.

````
Press ++ctrl+alt+delete++ to open the task manager.
````

Press ++ctrl+alt+delete++ to open the task manager.

### Critic Markup

Critic Markup shows proposed edits inline: additions, deletions, substitutions, comments, and highlights.

Critic Markup runs before a code fence can protect its text, so this source is written as escaped HTML to print the markers.
On your own pages, type the plain markers.

<pre><code>Proposed edit: {&#43;+added text+&#43;}, {&#45;-removed text-&#45;}, and {~&#126;old~&gt;new~&#126;}.
{&#61;=Highlighted text=&#61;}{&gt;&gt;A comment about it.&lt;&lt;}</code></pre>

Proposed edit: {++added text++}, {--removed text--}, and {~~old~>new~~}.
{==Highlighted text==}{>>A comment about it.<<}

### Smart Symbols

Common character sequences become typographic symbols.

````
(c) 2026, (tm), (r), 1/2, 3/4, +/-, =/=, -->, <--, <-->
````

(c) 2026, (tm), (r), 1/2, 3/4, +/-, =/=, -->, <--, <-->

### Emoji

Wrap a shortcode in colons.
The result is the character itself, so the page loads no image for it.

````
:smile: :tada: :rocket:
````

:smile: :tada: :rocket:

### Math

Dollar signs wrap math.
One pair is inline, two pairs set a block.
Bartleby writes the math markup; it does not ship a math renderer.
Inline math becomes `\(...\)` and a block becomes `\[...\]`, each inside an element with the `arithmatex` class.
MathJax 3 and KaTeX's auto-render script both read those delimiters as they come, so add either script to your templates to typeset the math.
Until you do, the result shows the TeX source between the delimiters.

````
The roots are $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.

$$
E = mc^2
$$
````

The roots are $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.

$$
E = mc^2
$$

## Blocks and Layout

### Content Tabs

Each `===` line starts a tab.
Indent the tab's content by four spaces.

````
=== "Python"

    ```python
    print("Hello")
    ```

=== "Bash"

    ```bash
    echo "Hello"
    ```
````

=== "Python"

    ```python
    print("Hello")
    ```

=== "Bash"

    ```bash
    echo "Hello"
    ```

### Collapsible Sections

`???` starts a section that is closed until the reader opens it.
`???+` starts one that is open.

````
??? note "Click to expand"

    This text was hidden until you opened it.

???+ tip "Open by default"

    This one starts open.
````

??? note "Click to expand"

    This text was hidden until you opened it.

???+ tip "Open by default"

    This one starts open.

### Admonitions

`!!!` starts a callout.
The word after it picks the style: `note`, `tip`, `warning`, `danger`, and more.

````
!!! warning "Check Before You Deploy"

    Set `site.url` in `bartleby.yml` first.
````

!!! warning "Check Before You Deploy"

    Set `site.url` in `bartleby.yml` first.

### Task Lists

Square brackets after a list dash draw a checkbox.

````
- [x] Run `bartleby serve`
- [x] Edit the home page
- [ ] Add a page of your own
````

- [x] Run `bartleby serve`
- [x] Edit the home page
- [ ] Add a page of your own

### Figures with Captions

A `caption` block wraps the paragraph above it in a figure.

````
![A blue slide](slide-1.svg)

/// caption
A figure with a caption.
///
````

![A blue slide](slide-1.svg)

/// caption
A figure with a caption.
///

## Standard Markdown Extras

### Tables

Pipes and dashes draw a table.
A colon in the dash row sets alignment.

````
| Feature | Where it lives | Status |
| :------ | :------------: | -----: |
| Tabs | pymdownx.tabbed | on |
| Embeds | markwright | on |
````

| Feature | Where it lives | Status |
| :------ | :------------: | -----: |
| Tabs | pymdownx.tabbed | on |
| Embeds | markwright | on |

### Footnotes

A bracketed caret marks a note, and a matching line defines it.

````
Bartleby builds the site in one pass.[^pass]

[^pass]: There is no incremental build; every run rebuilds every page.
````

Bartleby builds the site in one pass.[^pass]

[^pass]: There is no incremental build; every run rebuilds every page.

### Definition Lists

A term on one line and a colon on the next define it.

````
Front matter
:   The YAML block at the top of a page.

Content type
:   A directory of pages that share a listing and a set of options.
````

Front matter
:   The YAML block at the top of a page.

Content type
:   A directory of pages that share a listing and a set of options.

### Abbreviations

An asterisk line defines an abbreviation that shows its meaning on hover.

````
The HTML spec is maintained by the WHATWG.

*[HTML]: HyperText Markup Language
````

The HTML spec is maintained by the WHATWG.

*[HTML]: HyperText Markup Language

### Attribute Lists

Curly braces after an element add a class or an ID.

````
A paragraph with a custom class.
{: .tour-note #tour-note }
````

A paragraph with a custom class.
{: .tour-note #tour-note }

## Embeds

Embeds sit on a line of their own.
They load live, as soon as the page opens.
See the README for how to hold one back until the reader clicks it.

### YouTube

The video ID, then an optional height and width in pixels.

````
[youtube jNQXAC9IVRw]
````

[youtube jNQXAC9IVRw]

### CodePen

The user name, the pen's hash, then flags such as `dark`, `css`, or a height.

````
[codepen MattCowley vwPzeX]
````

[codepen MattCowley vwPzeX]

### Twitter

A tweet URL, then flags such as `dark`, `left`, or a width.

````
[twitter https://twitter.com/jack/status/20]
````

[twitter https://twitter.com/jack/status/20]

### Instagram

A post URL, then flags such as `caption`, `left`, or a width.

````
[instagram https://www.instagram.com/p/CkQuv3_LRgS]
````

[instagram https://www.instagram.com/p/CkQuv3_LRgS]

## Images

### Slideshow

List one or more image URLs.
Relative paths work, so images that sit next to the page travel with it.

````
[slideshow slide-1.svg slide-2.svg slide-3.svg]
````

[slideshow slide-1.svg slide-2.svg slide-3.svg]

### Image Compare

Two image URLs make a slider that wipes between them.

````
[compare before.svg after.svg]
````

[compare before.svg after.svg]

## Not Shown Here

`pymdownx.snippets` includes the text of another file with a `--8<--` line.
It needs a file to include, so this page leaves it out.
