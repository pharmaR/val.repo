#include <RcppArmadillo.h>
using namespace arma;

#include <Rcpp.h>

// [[Rcpp::depends(RcppArmadillo)]]

/*********************************************/
double betweenvarCpp (const arma::mat& tab, const arma::vec& pl, Rcpp::IntegerVector fac)
{
	double  s, bvar;
	int     i, j, icla;
	int l1 = tab.n_rows;
	int c1 = tab.n_cols;
	Rcpp::CharacterVector faclevs = fac.attr("levels");
	int ncla = faclevs.length();

	bvar = 0;
	for (j=0; j<c1; j++) {
		arma::vec m(ncla);
		arma::vec indicaw(ncla);
		for (i=0; i<l1; i++) {
			icla = fac(i) - 1;
			indicaw(icla) = indicaw(icla) + pl(i);
			m(icla) = m(icla) + tab(i, j) * pl(i);
		}
		s = 0;
		for (i=0; i<ncla; i++) {
			s = s + m(i) * m(i) / indicaw(i);
		}   
		bvar = bvar + s;
	}
	return (bvar);
}

/*********************************************/
double inerbetweenCpp (const arma::vec& pl, const arma::vec& pc, const int moda, Rcpp::IntegerVector indica, const arma::mat& tab)
{
  int i, j, k, l1, rang;
  double poi, a0, a1, s1;
  double inerb;
 
  l1 = tab.n_rows;
  rang = tab.n_cols;
  
  arma::mat moy(moda, rang);
  arma::vec pcla(moda);
  
  for (i=0; i<l1; i++) { 
    k = indica(i)-1;
    poi = pl(i);
    pcla(k)=pcla(k)+poi;
  }


  for (i=0; i<l1; i++) {
    k = indica(i)-1;
    poi = pl(i);
    for (j=0; j<rang; j++) {
      moy(k, j) = moy(k, j) + tab(i, j) * poi;
    }
  }
    
  for (k=0; k<moda; k++) { 
    a0 = pcla(k);
    for (j=0; j<rang; j++) {
      moy(k, j) = moy(k, j) / a0;
    }
  }

  inerb = 0;
  for (i=0; i<moda; i++) {
    a1 = pcla(i);
    for (j=0; j<rang; j++) {
      s1 = moy(i, j);
      inerb = inerb + s1 * s1 *a1 * pc(j);
    }
  }
  return inerb;
}

/*********************************************/
int matmodifcmCpp (arma::mat& tab, const arma::vec& poili)
{
/*--------------------------------------------------
 * tab est un tableau n lignes, m colonnes
 * disjonctif complet
 * poili est un vecteur n composantes
 * la procedure retourne tab centre par colonne 
 * pour la ponderation poili (somme=1)
 * centrage type correspondances multiples
 --------------------------------------------------*/
  double      poid;
  int             i, j;
  double      x, z;

	int l1 = tab.n_rows;
	int m1 = tab.n_cols;

	arma::vec      poimoda(m1, fill::zeros);


  for (i=0; i<l1; i++) {
    poid = poili(i);
    for (j=0; j<m1; j++) {
      poimoda(j) = poimoda(j) + tab(i,j) * poid;
    }
  }
    
  for (j=0; j<m1; j++) {
    x = poimoda(j);
    if (x==0) {
      for (i=0; i<l1; i++) tab(i,j) = 0;
    } else {
      for (i=0; i<l1; i++) {
		z = tab(i,j) / x - 1.0;
		tab(i,j) = z;
      }
    }
  }
  return 0;
}


/*********************************************/
int matmodifcnCpp (arma::mat& tab, const arma::vec& poili)
{
/*--------------------------------------------------
 * tab est un tableau n lignes, p colonnes
 * poili est un vecteur n composantes
 * la procedure retourne tab norme par colonne 
 * pour la ponderation poili (somme=1)
 --------------------------------------------------*/
  double      poid, x, z, y, v2;
  int             i, j;

	int l1 = tab.n_rows;
	int c1 = tab.n_cols;

	arma::vec      moy(c1, fill::zeros);
	arma::vec      var(c1, fill::zeros);


  /*--------------------------------------------------
   * calcul du tableau centre/norme
   --------------------------------------------------*/

  for (i=0; i<l1; i++) {
    poid = poili(i);
    for (j=0; j<c1; j++) {
      moy(j) = moy(j) + tab(i,j) * poid;
    }
  }
    
  for (i=0; i<l1; i++) {
    poid = poili(i);
    for (j=0; j<c1; j++) {
      x = tab(i,j) - moy(j);
      var(j) = var(j) + poid * x * x;
    }
  }
    
  for (j=0; j<c1; j++) {
    v2 = var(j);
    if (v2 <= 0) v2 = 1;
    v2 = sqrt(v2);
    var(j) = v2;
  }
    
  for (i=0; i<c1; i++) {
    x = moy(i);
    y = var(i);
    for (j=0; j<l1; j++) {
      z = tab(j,i) - x;
      z = z / y;
      tab(j,i) = z;
    }
  }
  return 0;
}


/*********************************************/
int matmodifcsCpp (arma::mat& tab, const arma::vec& poili)
{
/*--------------------------------------------------
 * tab est un tableau n lignes, p colonnes
 * poili est un vecteur n composantes
 * la procedure retourne tab standardise par colonne 
 * pour la ponderation poili (somme=1)
 --------------------------------------------------*/
  double      poid, x, z, y, v2;
  int         i, j;

	int l1 = tab.n_rows;
	int c1 = tab.n_cols;

	arma::vec      var(c1, fill::zeros);

  /*--------------------------------------------------
   * calcul du tableau standardise
   --------------------------------------------------*/

  for (i=0; i<l1; i++) {
    poid = poili(i);
    for (j=0; j<c1; j++) {
      x = tab(i,j);
      var(j) = var(j) + poid * x * x;
    }
  }
    
  for (j=0; j<c1; j++) {
    v2 = var(j);
    if (v2 <= 0) v2 = 1;
    v2 = sqrt(v2);
    var(j) = v2;
  }
    
  for (i=0; i<c1; i++) {
    y = var(i);
    for (j=0; j<l1; j++) {
      z = tab(j,i);
      z = z / y;
      tab(j,i) = z;
    }
  }
  return 0;
}


/*********************************************/
int matmodifcpCpp (arma::mat& tab, const arma::vec& poili)
{
/*--------------------------------------------------
 * tab est un tableau n lignes, p colonnes
 * poili est un vecteur n composantes
 * la procedure retourne tab centre par colonne 
 * pour la ponderation poili (somme=1)
 --------------------------------------------------*/
  double      poid;
  int             i, j;
  double      x, z;

	int l1 = tab.n_rows;
	int c1 = tab.n_cols;

	arma::vec      moy(c1);

  /*--------------------------------------------------
   * calcul du tableau centre
   --------------------------------------------------*/

  for (i=0; i<l1; i++) {
    poid = poili(i);
    for (j=0; j<c1; j++) {
      moy(j) = moy(j) + tab(i,j) * poid;
    }
  }
    
    
  for (i=0; i<c1; i++) {
    x = moy(i);
    for (j=0; j<l1; j++) {
      z = tab(j,i) - x;
      tab(j,i) = z;
    }
  }
  return 0;
}


/*********************************************/
int matmodiffcCpp (arma::mat& tab, const arma::vec& poili)
{
/*--------------------------------------------------
 * tab est un tableau n lignes, m colonnes
 * de nombres positifs ou nuls
 * poili est un vecteur n composantes
 * la procedure retourne tab centre doublement 
 * pour la ponderation poili (somme=1)
 * centrage type correspondances simples
 --------------------------------------------------*/
  int             i, j;
  double      x, z, poid;

	int l1 = tab.n_rows;
	int m1 = tab.n_cols;

  arma::vec      poimoda(m1);

  for (i=0; i<l1; i++) {
    x = 0;
    for (j=0; j<m1; j++) {
      x = x + tab(i,j);
    }
    if (x!=0) {
      for (j=0; j<m1; j++) {
		tab(i,j) = tab(i,j)/x;
      }
    }   
  }

  for (i=0; i<l1; i++) {
    poid = poili(i);
    for (j=0; j<m1; j++) {
      poimoda(j) = poimoda(j) + tab(i,j) * poid;
    }
  }
    
  for (j=0; j<m1; j++) {
    x = poimoda(j);
    if (x==0) {
      /* err_message("column has a nul weight (matmodiffc)"); */
      Rcpp::Rcout << "column with nul weight (matmodiffc)" << x << std::endl;
    }
        
    for (i=0; i<l1; i++) {
      z = tab(i,j) / x - 1.0;
      tab(i,j) = z;
    }
  }
  return 0;
}


/*********************************************/
int matcentrageCpp (arma::mat& A, const arma::vec& poili, const int typ)
{
  /* Modification of the original table for different analyses.
     typ=1 no modification (PCA on original variable)
     typ=2 ACM (matmodifcm)
     typ=3 normed and centred PCA (matmodifcn)
     typ=4 centred PCA (matmodifcp)
     typ=5 normed and non-centred PCA (matmodifcs)
     typ=6 COA (matmodiffc)
     typ=7 FCA (matmodiffc)
     typ=8 Hill-smith (use matcentagehi in this case)
  */
  if (typ == 1) {
    return 0;
  } else if (typ == 2) {
    matmodifcmCpp (A, poili);
    return 0;
  } else if (typ == 3) {
    matmodifcnCpp (A, poili);
    return 0;
  } else if (typ == 4) {
    matmodifcpCpp (A, poili);
    return 0;
  } else if (typ == 5) {
    matmodifcsCpp (A, poili);
    return 0;
  } else if (typ == 6) {
    matmodiffcCpp (A, poili);
    return 0;
  } else if (typ == 7) {
    matmodifcmCpp (A, poili);
    return 0;
  }
  return 0;
}

