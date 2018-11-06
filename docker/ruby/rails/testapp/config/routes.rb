Rails.application.routes.draw do
  # For details on the DSL available within this file, see http://guides.rubyonrails.org/routing.html
  get 'healthcheck', to:'application#healthcheck'
  get 'foo', to: 'application#foo'
  get 'bar', to: 'application#bar'
  get 'oof', to: 'application#oof'
end
